/* Geek Koşusu 3D — Geek logolu tişörtlü barista ile üç şeritli, tam ekran sonsuz koşu (three.js).
   Kontrol: ← → / A D şerit · ↑ / W / Boşluk zıpla · ↓ / S kay · P duraklat
   Dokunmatik: kaydır (sağ/sol/yukarı/aşağı), dokunmak = zıpla.
   Her 1000 metrede hız bir kademe artar. */
(function () {
  'use strict';
  var kok = document.getElementById('kosu-oyun');
  if (!kok || !window.THREE) return;
  var T = THREE;
  try { T.ColorManagement.enabled = true; } catch (e) {}

  /* ---------- sabitler ---------- */
  var SERIT = 2.4;                       // şerit genişliği
  var CIZIM_UZAK = 150;
  var YERCEKIMI = 30, ZIPLAMA_V = 11.2;
  var SEVIYE_M = 1000;                   // her 1000 metrede bir hız kademesi
  var MAVI = 0x2a3bd6, KREMA = 0xf2b544, LACI = 0x0b0f2e;
  var URL_SKOR = kok.getAttribute('data-skor-url');
  var LOGO_URL = kok.getAttribute('data-logo');
  var CSRF = (document.querySelector('input[name=csrfmiddlewaretoken]') || {}).value || '';
  var ENIYI = parseInt(kok.getAttribute('data-en') || '0', 10) || 0;
  var DEBUG = /kosudebug/.test(location.search);

  /* Hız (dünya birimi/sn). Ekranda gösterilen "metre" = dünya birimi × METRE_KAT; her 1000 m'de bir kademe artar.
     Koşu animasyonu bu hıza bağlı (adım sıklığı = hız / ADIM_BOY) — yol ile karakter aynı tempoda akar. */
  var METRE_KAT = 1.5;
  var ADIM_BOY = 2.9;                    // bir tam adım döngüsünde (sol+sağ) kat edilen dünya birimi
  function hizSeviyeye(sev) { return Math.min(9.5 + (sev - 1) * 1.35, 16); }

  /* ---------- DOM ---------- */
  function $(id) { return document.getElementById(id); }
  var elSahne = $('kosu-sahne'), elMenu = $('kosu-menu'), elBitis = $('kosu-bitis'), elDur = $('kosu-dur');
  var hSkor = $('kh-skor'), hCekirdek = $('kh-cekirdek'), hMesafe = $('kh-mesafe'), hSev = $('kh-sev'), hSevBar = $('kh-sev-bar');
  var hGucBar = $('kh-guc-bar'), hGucKap = $('kh-guc-bar').closest('.kh-guc-kap'), hMesaj = $('kh-mesaj'), hGeri = $('kh-geri'), elFlas = $('kosu-flas'), sesBtn = $('kosu-ses');

  /* ---------- ses ---------- */
  var ses = { ctx: null, kapali: false };
  try { ses.kapali = localStorage.getItem('kosu_ses') === '0'; } catch (e) {}
  function sesBaslat() {
    if (!ses.ctx) { try { ses.ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} }
    if (ses.ctx && ses.ctx.state === 'suspended') ses.ctx.resume();
  }
  function bip(f, s, tip, v, f2, gecikme) {
    if (ses.kapali || !ses.ctx) return;
    var c = ses.ctx, t = c.currentTime + (gecikme || 0);
    var o = c.createOscillator(), g = c.createGain();
    o.type = tip || 'sine'; o.frequency.setValueAtTime(f, t);
    if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + s);
    g.gain.setValueAtTime(v || 0.12, t); g.gain.exponentialRampToValueAtTime(0.0001, t + s);
    o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + s + 0.02);
  }
  function gurultu(s, v) {
    if (ses.kapali || !ses.ctx) return;
    var c = ses.ctx, n = Math.floor(c.sampleRate * s), b = c.createBuffer(1, n, c.sampleRate), d = b.getChannelData(0);
    for (var i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    var k = c.createBufferSource(), g = c.createGain(); k.buffer = b; g.gain.value = v || 0.25;
    k.connect(g); g.connect(c.destination); k.start();
  }
  var SES = {
    ziplama: function () { bip(300, 0.16, 'square', 0.06, 640); },
    kayma: function () { gurultu(0.22, 0.1); bip(260, 0.18, 'sawtooth', 0.04, 110); },
    serit: function () { bip(420, 0.06, 'triangle', 0.05, 520); },
    adim: function () { bip(90, 0.05, 'sine', 0.035, 60); },
    cekirdek: function (kombo) { bip(880 * Math.pow(1.06, Math.min(kombo, 10)), 0.12, 'sine', 0.1, 1500); },
    guc: function () { [523, 659, 784, 1046].forEach(function (f, i) { bip(f, 0.18, 'triangle', 0.1, 0, i * 0.07); }); },
    carpma: function () { gurultu(0.5, 0.35); bip(160, 0.5, 'sawtooth', 0.12, 40); },
    kirma: function () { gurultu(0.25, 0.2); bip(500, 0.12, 'square', 0.06, 200); },
    seviye: function () { [392, 523, 659, 784, 1046].forEach(function (f, i) { bip(f, 0.2, 'triangle', 0.1, 0, i * 0.08); }); },
    soguk: function () { bip(900, 0.5, 'sine', 0.09, 180); bip(450, 0.6, 'triangle', 0.05, 90, 0.1); },
    mikn: function () { [300, 380, 480, 600].forEach(function (f, i) { bip(f, 0.14, 'square', 0.04, f * 1.4, i * 0.05); }); },
    simsek: function () { gurultu(1.1, 0.28); bip(70, 0.9, 'sawtooth', 0.1, 30, 0.05); },
    geri: function (son) { bip(son ? 880 : 520, son ? 0.35 : 0.14, 'square', 0.07); }
  };
  function sesGuncelle() { if (sesBtn) { sesBtn.setAttribute('aria-pressed', ses.kapali ? 'false' : 'true'); sesBtn.textContent = ses.kapali ? 'Ses kapalı' : 'Ses açık'; } }
  sesGuncelle();
  if (sesBtn) sesBtn.addEventListener('click', function () {
    ses.kapali = !ses.kapali; try { localStorage.setItem('kosu_ses', ses.kapali ? '0' : '1'); } catch (e) {}
    sesBaslat(); sesGuncelle();
  });

  /* ---------- Geek Radio (kabuktaki ortak oynatıcı; oyundan kapatılabilir/açılabilir) ---------- */
  var radyoR = null;
  function radyoKur() {
    if (radyoR || !window.GeekRadyoAl) return;
    radyoR = GeekRadyoAl({ api: kok.dataset.radyoApi, yedek: kok.dataset.radyoYedek, sayfa: kok.dataset.radyoSayfa });
    radyoR.abone(function (d) {
      [].forEach.call(document.querySelectorAll('[data-kosu-radyo]'), function (b) {
        b.setAttribute('aria-pressed', d.ister ? 'true' : 'false');
        b.textContent = (b.dataset.kosuRadyo === 'menu') ? (d.ister ? '♪ Radyoyu kapat' : '♪ Geek Radio\'yu aç') : (d.ister ? '♪ Radyo açık' : '♪ Radyo');
      });
      var bilgi = d.ister ? ('♪ ' + d.sarki + (d.sanatci ? ' · ' + d.sanatci : '')) : '';
      [].forEach.call(document.querySelectorAll('[data-kosu-radyo-bilgi]'), function (e) { e.textContent = bilgi; e.hidden = !bilgi; });
    });
  }
  function radyoDegistir() { radyoKur(); if (radyoR) radyoR.degistir(); }

  /* ---------- durum ---------- */
  var renderer, scene, kamera, hemi, gunes, dolgu, motorHazir = false;
  var B = {}, dunya = {}, fx = {};
  var durum = 'menu';                    // menu | oyun | dur | bitis
  var G = null;
  var logoImg = new Image(), logoYuklendi = false, logoTexler = [];
  var parcaciklar = [];
  var kalite = { pr: 1, top: 0, n: 0, golge: true, dusuruldu: 0 };

  /* ---------- yardımcılar ---------- */
  function std(renk, ekstra) {
    var o = { color: renk, roughness: 0.6, metalness: 0.0 };
    if (ekstra) for (var k in ekstra) o[k] = ekstra[k];
    return new T.MeshStandardMaterial(o);
  }
  function srgb(tex) { tex.encoding = T.sRGBEncoding; return tex; }
  function golgeli(obj, at, al) {
    obj.traverse(function (m) { if (m.isMesh) { m.castShadow = at !== false; m.receiveShadow = !!al; } });
    return obj;
  }
  function mesh(geo, mat, x, y, z) { var m = new T.Mesh(geo, mat); if (x !== undefined) m.position.set(x, y, z); return m; }

  function logoTexture(zemin, w, h, oran, renk) {
    var cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    var tex = srgb(new T.CanvasTexture(cv)); tex.anisotropy = 4;
    tex.userData.ayar = function (z, r) { zemin = z; renk = r; ciz(); };   // kıyafet değişince baskı rengi yenilenir
    function ciz() {
      var c = cv.getContext('2d'); c.clearRect(0, 0, w, h);
      if (zemin) { c.fillStyle = zemin; c.fillRect(0, 0, w, h); }
      if (logoYuklendi) {
        var lw = w * (oran || 0.78), lh = lw * logoImg.naturalHeight / logoImg.naturalWidth;
        if (lh > h * 0.88) { lh = h * 0.88; lw = lh * logoImg.naturalWidth / logoImg.naturalHeight; }
        var lx = (w - lw) / 2, ly = (h - lh) / 2;
        if (renk) {   // logoyu tek renge boya (koyu zeminde okunsun diye)
          var t = document.createElement('canvas'); t.width = Math.ceil(lw); t.height = Math.ceil(lh);
          var tc = t.getContext('2d'); tc.drawImage(logoImg, 0, 0, lw, lh);
          tc.globalCompositeOperation = 'source-in'; tc.fillStyle = renk; tc.fillRect(0, 0, lw, lh);
          c.drawImage(t, lx, ly);
        } else c.drawImage(logoImg, lx, ly, lw, lh);
      } else {
        c.fillStyle = renk || '#2a3bd6'; c.font = '800 ' + Math.floor(h * 0.6) + 'px system-ui,sans-serif';
        c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('geek', w / 2, h / 2);
      }
      tex.needsUpdate = true;
    }
    ciz(); logoTexler.push(ciz);
    return tex;
  }
  logoImg.onload = function () { logoYuklendi = true; logoTexler.forEach(function (f) { f(); }); };
  logoImg.src = LOGO_URL;

  function parlamaDokusu() {
    var cv = document.createElement('canvas'); cv.width = cv.height = 64;
    var c = cv.getContext('2d'), g = c.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.35, 'rgba(255,255,255,.45)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    c.fillStyle = g; c.fillRect(0, 0, 64, 64);
    return srgb(new T.CanvasTexture(cv));
  }
  function bulutDokusu() {
    var cv = document.createElement('canvas'); cv.width = 256; cv.height = 128;
    var c = cv.getContext('2d');
    for (var i = 0; i < 9; i++) {
      var x = 40 + i * 22 + Math.random() * 10, y = 70 + Math.random() * 14 - (i % 3) * 10, r = 24 + Math.random() * 20;
      var g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, 'rgba(255,255,255,.95)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      c.fillStyle = g; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill();
    }
    return srgb(new T.CanvasTexture(cv));
  }
  var glowTex = null;
  function parlama(renk, olcek, opak) {
    if (!glowTex) glowTex = parlamaDokusu();
    var s = new T.Sprite(new T.SpriteMaterial({ map: glowTex, color: renk, transparent: true, opacity: opak === undefined ? 0.8 : opak, blending: T.AdditiveBlending, depthWrite: false }));
    s.scale.set(olcek, olcek, 1); return s;
  }

  /* =====================================================================
     BARİSTA KARAKTER: Geek logolu tişört, önlük, kasket, elinde kahve
     ===================================================================== */
  function baristaKur() {
    var grup = new T.Group(), olc = 0.84;
    var deri = std(0xe6b08a, { roughness: 0.65 }), tisort = std(0xfdf6e6, { roughness: 0.85 }), onluk = std(LACI, { roughness: 0.8 });
    var kot = std(0x2d3d6e, { roughness: 0.9 }), sac = std(0x4a2c17, { roughness: 0.9 }), sapka = std(0x16205a, { roughness: 0.85 });
    var krem = std(KREMA, { roughness: 0.5 }), beyaz = std(0xffffff, { roughness: 0.45 });
    B.m = { tisort: tisort, onluk: onluk, sapka: sapka, ten: deri, sac: sac };

    var kalca = new T.Group(); kalca.position.y = 0.92; grup.add(kalca); B.kalca = kalca;
    var govde = new T.Group(); kalca.add(govde); B.govde = govde;
    // tişört
    var gv = mesh(new T.CylinderGeometry(0.265, 0.235, 0.64, 22), tisort, 0, 0.32, 0); gv.scale.z = 0.62; govde.add(gv);
    var omuz = mesh(new T.SphereGeometry(0.27, 18, 12), tisort, 0, 0.62, 0); omuz.scale.set(1.05, 0.34, 0.64); govde.add(omuz);
    // sırtta büyük Geek baskısı
    B.baskiTex = logoTexture('#fdf6e6', 512, 256, 0.98);
    var baski = mesh(new T.PlaneGeometry(0.5, 0.25), new T.MeshBasicMaterial({ map: B.baskiTex, toneMapped: false }), 0, 0.37, 0.172);
    govde.add(baski);
    // önlük: bel + göğüs, yakıt boyun bağı
    var onluk1 = mesh(new T.BoxGeometry(0.4, 0.46, 0.03), onluk, 0, 0.24, -0.168); govde.add(onluk1);
    var yama = mesh(new T.PlaneGeometry(0.2, 0.1), new T.MeshBasicMaterial({ map: logoTexture('#ffffff', 256, 128, 0.9), toneMapped: false }), 0, 0.32, -0.186); yama.rotation.y = Math.PI; govde.add(yama);
    var kemer = mesh(new T.BoxGeometry(0.56, 0.05, 0.3), onluk, 0, 0.05, 0); kemer.scale.z = 0.62; govde.add(kemer);
    var fiyonk1 = mesh(new T.BoxGeometry(0.1, 0.04, 0.02), krem, -0.07, 0.06, 0.2); fiyonk1.rotation.z = 0.5; govde.add(fiyonk1);
    var fiyonk2 = mesh(new T.BoxGeometry(0.1, 0.04, 0.02), krem, 0.07, 0.06, 0.2); fiyonk2.rotation.z = -0.5; govde.add(fiyonk2);
    var bag1 = mesh(new T.BoxGeometry(0.03, 0.2, 0.02), krem, -0.05, -0.04, 0.2); bag1.rotation.z = 0.15; govde.add(bag1);
    var bag2 = mesh(new T.BoxGeometry(0.03, 0.2, 0.02), krem, 0.05, -0.04, 0.2); bag2.rotation.z = -0.15; govde.add(bag2);
    // boyun + kafa
    govde.add(mesh(new T.CylinderGeometry(0.075, 0.085, 0.12, 12), deri, 0, 0.7, 0));
    var bas = new T.Group(); bas.position.y = 0.97; govde.add(bas); B.bas = bas;
    var kafa = mesh(new T.SphereGeometry(0.27, 24, 18), deri); kafa.scale.set(1, 1.04, 1.02); bas.add(kafa);
    [-1, 1].forEach(function (s) { bas.add(mesh(new T.SphereGeometry(0.06, 10, 8), deri, s * 0.265, -0.02, 0.01)); });
    // saç (arka ve yanlar) + kasket
    var sacM = mesh(new T.SphereGeometry(0.285, 20, 14, 0, Math.PI * 2, Math.PI * 0.2, Math.PI * 0.55), sac, 0, 0.0, 0.03); bas.add(sacM);
    var kuyruk = mesh(new T.SphereGeometry(0.14, 12, 10), sac, 0, -0.08, 0.2); kuyruk.scale.set(1.2, 0.9, 0.8); bas.add(kuyruk);
    var hKasket = new T.Group(); hKasket.position.y = 0.07; bas.add(hKasket);
    var kasket = mesh(new T.SphereGeometry(0.295, 22, 12, 0, Math.PI * 2, 0, Math.PI * 0.42), sapka, 0, 0.05, 0); kasket.scale.set(1.04, 0.85, 1.08); hKasket.add(kasket);
    var bant = mesh(new T.CylinderGeometry(0.285, 0.29, 0.045, 22), krem, 0, 0.075, 0); bant.scale.z = 1.05; hKasket.add(bant);
    var siper = mesh(new T.BoxGeometry(0.3, 0.025, 0.2), sapka, 0, 0.07, -0.3); siper.rotation.x = 0.12; hKasket.add(siper);
    var kyama = mesh(new T.PlaneGeometry(0.17, 0.075), new T.MeshBasicMaterial({ map: logoTexture('#fdf6e6', 256, 112, 0.9), toneMapped: false }), 0, 0.2, 0.275); kyama.rotation.x = -0.45; hKasket.add(kyama);
    // alternatif şapkalar (dolaptan seçilir)
    var beyazSapka = std(0xffffff, { roughness: 0.9 });
    var hSef = new T.Group(); hSef.visible = false; hSef.position.y = 0.05; bas.add(hSef);
    hSef.add(mesh(new T.CylinderGeometry(0.285, 0.29, 0.12, 22), beyazSapka, 0, 0.12, 0));
    var sefUst = mesh(new T.SphereGeometry(0.34, 22, 16), beyazSapka, 0, 0.36, 0); sefUst.scale.set(1.0, 0.82, 1.0); hSef.add(sefUst);
    [[-0.2, 0.3, 0.05], [0.2, 0.3, -0.05], [0.0, 0.42, 0.2], [0, 0.44, -0.18]].forEach(function (q) { hSef.add(mesh(new T.SphereGeometry(0.17, 14, 10), beyazSapka, q[0], q[1], q[2])); });
    var sefYama = mesh(new T.PlaneGeometry(0.17, 0.07), new T.MeshBasicMaterial({ map: logoTexture('#ffffff', 256, 104, 0.9), toneMapped: false }), 0, 0.12, -0.296); sefYama.rotation.y = Math.PI; hSef.add(sefYama);
    var bereM = std(0x10122a, { roughness: 0.95 }); B.m.bere = bereM;
    var hBere = new T.Group(); hBere.visible = false; bas.add(hBere);
    var bere = mesh(new T.SphereGeometry(0.305, 22, 14, 0, Math.PI * 2, 0, Math.PI * 0.48), bereM, 0, 0.07, 0); bere.scale.set(1.04, 1.0, 1.08); hBere.add(bere);
    var kivrim = mesh(new T.TorusGeometry(0.285, 0.055, 10, 26), bereM, 0, 0.1, 0); kivrim.rotation.x = Math.PI / 2; kivrim.scale.set(1.04, 1.1, 1); hBere.add(kivrim);
    hBere.add(mesh(new T.SphereGeometry(0.095, 12, 10), std(0xffffff, { roughness: 1 }), 0, 0.38, 0));
    var tacM = std(0xf2b544, { roughness: 0.25, metalness: 0.6, emissive: 0x6a4500, emissiveIntensity: 0.6 });
    var hTac = new T.Group(); hTac.visible = false; bas.add(hTac);
    hTac.add(mesh(new T.CylinderGeometry(0.25, 0.27, 0.12, 20), tacM, 0, 0.27, 0));
    for (var ti = 0; ti < 6; ti++) {
      var ta = ti / 6 * Math.PI * 2, sp = mesh(new T.ConeGeometry(0.058, 0.2, 8), tacM, Math.cos(ta) * 0.25, 0.43, Math.sin(ta) * 0.25); hTac.add(sp);
      hTac.add(mesh(new T.SphereGeometry(0.04, 8, 6), std(ti % 2 ? 0xe0554b : 0x38c8ff, { emissive: ti % 2 ? 0x601010 : 0x104060 }), Math.cos(ta) * 0.25, 0.55, Math.sin(ta) * 0.25));
    }
    B.sapkalar = { kasket: hKasket, sef: hSef, bere: hBere, tac: hTac };
    // güneş gözlüğü
    var gozlukGrup = new T.Group(); gozlukGrup.visible = false; bas.add(gozlukGrup);
    var camKoyu = std(0x0b0f1c, { roughness: 0.08, metalness: 0.3, emissive: 0x0a1020, emissiveIntensity: 0.5 });
    [-1, 1].forEach(function (sx) {
      var cam = mesh(new T.BoxGeometry(0.13, 0.095, 0.02), camKoyu, sx * 0.105, 0.012, -0.283); gozlukGrup.add(cam);
      var kenar = mesh(new T.BoxGeometry(0.15, 0.115, 0.014), std(0x16183a, { roughness: 0.4 }), sx * 0.105, 0.012, -0.277); gozlukGrup.add(kenar);
      var kol = mesh(new T.BoxGeometry(0.014, 0.014, 0.24), std(0x16183a), sx * 0.2, 0.025, -0.16); gozlukGrup.add(kol);
    });
    gozlukGrup.add(mesh(new T.BoxGeometry(0.06, 0.016, 0.016), std(0x16183a), 0, 0.03, -0.285));
    // kulaklık
    var kulakGrup = new T.Group(); kulakGrup.visible = false; bas.add(kulakGrup);
    var kulakM = std(0x1d2145, { roughness: 0.4, metalness: 0.2 });
    var bandK = mesh(new T.TorusGeometry(0.335, 0.026, 10, 28, Math.PI), kulakM, 0, 0.0, 0); bandK.rotation.z = 0; kulakGrup.add(bandK);
    [-1, 1].forEach(function (sx) {
      var kp = mesh(new T.CylinderGeometry(0.1, 0.1, 0.075, 18), kulakM, sx * 0.335, -0.01, 0); kp.rotation.z = Math.PI / 2; kulakGrup.add(kp);
      var kc = mesh(new T.CylinderGeometry(0.075, 0.075, 0.02, 16), std(0xf2b544, { emissive: 0x6a4500, emissiveIntensity: 0.6 }), sx * 0.378, -0.01, 0); kc.rotation.z = Math.PI / 2; kulakGrup.add(kc);
    });
    B.gozluk = gozlukGrup; B.kulaklik = kulakGrup;
    // atkı
    var atkiM = std(0xf2b544, { roughness: 0.95 }); B.m.atki = atkiM;
    var atki = new T.Group(); atki.visible = false; govde.add(atki);
    var atkiHalka = mesh(new T.TorusGeometry(0.17, 0.065, 10, 22), atkiM, 0, 0.7, 0); atkiHalka.rotation.x = Math.PI / 2; atkiHalka.scale.set(1.1, 1, 1.1); atki.add(atkiHalka);
    var atkiKuyruk = mesh(new T.BoxGeometry(0.12, 0.42, 0.04), atkiM, 0.1, 0.5, 0.2); atkiKuyruk.rotation.z = 0.12; atki.add(atkiKuyruk);
    B.atki = atki;
    // yüz (önden bakınca görünür)
    [-1, 1].forEach(function (s) {
      bas.add(mesh(new T.SphereGeometry(0.048, 12, 10), beyaz, s * 0.1, 0.015, -0.235));
      bas.add(mesh(new T.SphereGeometry(0.027, 10, 8), std(0x1a1208, { roughness: 0.3 }), s * 0.1, 0.012, -0.275));
      var kas = mesh(new T.BoxGeometry(0.09, 0.018, 0.02), sac, s * 0.1, 0.095, -0.255); kas.rotation.z = s * 0.15; bas.add(kas);
    });
    bas.add(mesh(new T.SphereGeometry(0.04, 10, 8), std(0xd89a74), 0, -0.04, -0.29));
    var biyik = mesh(new T.BoxGeometry(0.17, 0.035, 0.03), sac, 0, -0.1, -0.27); bas.add(biyik);
    var gulus = mesh(new T.TorusGeometry(0.07, 0.014, 8, 14, Math.PI), std(0x7a2f2f), 0, -0.13, -0.255); gulus.rotation.z = Math.PI; bas.add(gulus);
    // kollar
    function kol(s) {
      var omz = new T.Group(); omz.position.set(s * 0.335, 0.56, 0); govde.add(omz);
      omz.add(mesh(new T.CylinderGeometry(0.1, 0.092, 0.27, 12), tisort, 0, -0.12, 0));
      var dirsek = new T.Group(); dirsek.position.y = -0.26; omz.add(dirsek);
      dirsek.add(mesh(new T.CylinderGeometry(0.068, 0.058, 0.3, 10), deri, 0, -0.15, 0));
      dirsek.add(mesh(new T.SphereGeometry(0.078, 12, 10), deri, 0, -0.32, 0));
      return { omz: omz, dirsek: dirsek };
    }
    var kSol = kol(-1), kSag = kol(1);
    B.shL = kSol.omz; B.elL = kSol.dirsek; B.shR = kSag.omz; B.elR = kSag.dirsek;
    // sağ elde Geek logolu take-away kahve
    var fb = new T.Group(); fb.position.set(0, -0.34, -0.03); kSag.dirsek.add(fb);
    var fg = mesh(new T.CylinderGeometry(0.1, 0.075, 0.26, 16), beyaz, 0, 0.1, 0); fb.add(fg);
    fb.add(mesh(new T.CylinderGeometry(0.108, 0.104, 0.05, 16), onluk, 0, 0.25, 0));
    fb.add(mesh(new T.CylinderGeometry(0.1, 0.09, 0.09, 16, 1, true), krem, 0, 0.1, 0));
    var fl = mesh(new T.PlaneGeometry(0.15, 0.07), new T.MeshBasicMaterial({ map: logoTexture('#ffffff', 256, 120, 0.95), toneMapped: false }), 0, 0.12, 0.112); fb.add(fl);
    B.fincan = fb;
    // bacaklar
    function bacak(s) {
      var kalcaP = new T.Group(); kalcaP.position.set(s * 0.135, 0, 0); kalca.add(kalcaP);
      kalcaP.add(mesh(new T.CylinderGeometry(0.115, 0.095, 0.48, 12), kot, 0, -0.23, 0));
      var diz = new T.Group(); diz.position.y = -0.47; kalcaP.add(diz);
      diz.add(mesh(new T.CylinderGeometry(0.092, 0.075, 0.44, 12), kot, 0, -0.21, 0));
      var ayak = new T.Group(); ayak.position.y = -0.45; diz.add(ayak);
      var ust = mesh(new T.SphereGeometry(0.12, 14, 10), beyaz, 0, 0.0, -0.05); ust.scale.set(0.95, 0.62, 1.55); ayak.add(ust);
      ayak.add(mesh(new T.BoxGeometry(0.2, 0.045, 0.4), krem, 0, -0.065, -0.07));
      ayak.add(mesh(new T.BoxGeometry(0.205, 0.04, 0.12), std(0xe0554b), 0, -0.01, -0.2));   // burun çizgisi
      return { kalcaP: kalcaP, diz: diz };
    }
    var bL = bacak(-1), bR = bacak(1);
    B.hipL = bL.kalcaP; B.kneeL = bL.diz; B.hipR = bR.kalcaP; B.kneeR = bR.diz;

    grup.scale.setScalar(olc);
    golgeli(grup, true, false);
    B.grup = grup; B.olc = olc;
    // gölge ve kalkan
    B.golge = mesh(new T.CircleGeometry(0.7, 24), new T.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.3, depthWrite: false }));
    B.golge.rotation.x = -Math.PI / 2; B.golge.position.y = 0.025;
    B.kalkan = mesh(new T.SphereGeometry(1.55, 28, 20), new T.MeshBasicMaterial({ color: 0xffd36a, transparent: true, opacity: 0.2, depthWrite: false }), 0, 1.0, 0);
    B.kalkan.visible = false; grup.add(B.kalkan); B.kalkan.scale.setScalar(1 / olc);
    B.aura = parlama(0xffd36a, 4.2, 0.0); B.aura.position.y = 1.0; grup.add(B.aura);
    scene.add(grup); scene.add(B.golge);
  }

  /* poz: mod = kos | ziplama | kayma | bekle | selam */
  function poz(mod, ph, t, zamanDt) {
    var s = Math.sin(ph), c = Math.cos(ph), k = 0.25;
    var yumus = Math.min(1, zamanDt * 18);
    function git(obj, ek, v) { obj.rotation[ek] += (v - obj.rotation[ek]) * yumus; }
    var hL = 0, hR = 0, kL = 0, kR = 0, sL = 0, sR = 0, eL = 0, eR = 0, egim = 0, basX = 0, yuk = 0.92, gx = 0;
    if (mod === 'kos') {
      var gOr = (G && G.hizOr) || 0, amp = 0.95 + gOr * 0.22;
      hL = s * amp; hR = -s * amp;
      kL = -(0.2 + Math.max(0, c) * 1.15); kR = -(0.2 + Math.max(0, -c) * 1.15);
      sL = -s * 1.05; sR = s * 0.5 + 0.55;
      eL = 0.95 + Math.max(0, c) * 0.25; eR = 1.55;
      egim = -0.2 - gOr * 0.08 + c * 0.03; basX = 0.08;
      yuk = 0.92 + Math.abs(c) * 0.075;
    } else if (mod === 'ziplama') {
      hL = 0.95; kL = -0.7; hR = -0.3; kR = -1.35;
      sL = 2.7; sR = 2.1; eL = 0.25; eR = 0.9; egim = -0.12; basX = -0.15; yuk = 0.96;
    } else if (mod === 'kayma') {
      hL = 0.1; hR = 0.0; kL = -0.12; kR = -0.05; sL = 2.4; sR = 2.2; eL = 0.1; eR = 0.5; egim = 1.22; yuk = 0.46; basX = -0.7;
    } else if (mod === 'selam') {
      hL = 0.02; hR = -0.02; kL = -0.03; kR = -0.03; sL = 2.9 + Math.sin(t * 7) * 0.35; eL = 0.5 + Math.sin(t * 7) * 0.4; sR = 0.1; eR = 1.0; egim = 0; basX = 0; yuk = 0.92 + Math.sin(t * 2.5) * 0.01;
    } else {   // bekle
      hL = 0.04; hR = -0.04; kL = -0.04; kR = -0.04; sL = 0.05; sR = 0.1; eL = 0.15; eR = 1.2; egim = -0.03; basX = 0; yuk = 0.92 + Math.sin(t * 2.5) * 0.012;
    }
    git(B.hipL, 'x', hL); git(B.hipR, 'x', hR); git(B.kneeL, 'x', kL); git(B.kneeR, 'x', kR);
    git(B.shL, 'x', sL); git(B.shR, 'x', sR); git(B.elL, 'x', eL); git(B.elR, 'x', eR);
    git(B.kalca, 'x', egim); git(B.bas, 'x', basX);
    B.shL.rotation.z = -0.1 - (mod === 'ziplama' ? 0.25 : 0); B.shR.rotation.z = 0.1 + (mod === 'ziplama' ? 0.25 : 0);
    B.kalca.position.y += (yuk - B.kalca.position.y) * Math.min(1, zamanDt * 20);
    B.bas.rotation.z = mod === 'kos' ? s * 0.04 : 0;
  }


  /* =====================================================================
     DOLAP: seçilebilir kıyafetler, ten rengi, aksesuarlar (en iyi skorla açılır)
     ===================================================================== */
  var DOLAP = [
    { id: 'klasik', ad: 'Klasik Barista', kilit: 0,    tisort: 0xfdf6e6, baskiZ: '#fdf6e6', baskiR: null,      onluk: 0x0b0f2e, sapka: 'kasket', sapkaR: 0x16205a, atki: 0,        emis: 0 },
    { id: 'mavi',   ad: 'Geek Mavi',      kilit: 0,    tisort: 0x2a3bd6, baskiZ: '#2a3bd6', baskiR: '#f2b544', onluk: 0xf4e9cf, sapka: 'kasket', sapkaR: 0xf2b544, atki: 0,        emis: 0 },
    { id: 'retro',  ad: 'Retro Kırmızı',  kilit: 400,  tisort: 0xe0554b, baskiZ: '#e0554b', baskiR: '#fdf6e6', onluk: 0xf2e6c8, sapka: 'kasket', sapkaR: 0xf2e6c8, atki: 0,        emis: 0 },
    { id: 'sef',    ad: 'Şef Geek',       kilit: 1000, tisort: 0xffffff, baskiZ: '#ffffff', baskiR: '#2a3bd6', onluk: 0xdfe4f5, sapka: 'sef',    sapkaR: 0xffffff, atki: 0,        emis: 0 },
    { id: 'gece',   ad: 'Neon Gece',      kilit: 2000, tisort: 0x10122a, baskiZ: '#10122a', baskiR: '#38f2ff', onluk: 0x232a63, sapka: 'bere',   sapkaR: 0x10122a, atki: 0,        emis: 0x063a4a },
    { id: 'kis',    ad: 'Kış Keyfi',      kilit: 3500, tisort: 0xb3283a, baskiZ: '#b3283a', baskiR: '#ffffff', onluk: 0x2b2f45, sapka: 'bere',   sapkaR: 0xf2b544, atki: 0xf2b544, emis: 0 },
    { id: 'altin',  ad: 'Altın Şampiyon', kilit: 6000, tisort: 0xf2b544, baskiZ: '#f2b544', baskiR: '#0b0f2e', onluk: 0x0b0f2e, sapka: 'tac',    sapkaR: 0x16205a, atki: 0,        emis: 0x4a3000 }
  ];
  var TENLER = [0xf6d6bb, 0xe6b08a, 0xc68642, 0x8d5524];
  var TEN_AD = ['Açık', 'Buğday', 'Bronz', 'Koyu'];
  var K = { k: 'klasik', ten: 1, gozluk: false, kulaklik: false };
  try {
    var kk = JSON.parse(localStorage.getItem('kosu_dolap') || 'null');
    if (kk) {
      if (DOLAP.some(function (o) { return o.id === kk.k; })) K.k = kk.k;
      if (kk.ten >= 0 && kk.ten < TENLER.length) K.ten = kk.ten;
      K.gozluk = !!kk.gozluk; K.kulaklik = !!kk.kulaklik;
    }
  } catch (e) {}
  function dolapKaydet() { try { localStorage.setItem('kosu_dolap', JSON.stringify(K)); } catch (e) {} }
  function kiyafetBul(id) { for (var i = 0; i < DOLAP.length; i++) if (DOLAP[i].id === id) return DOLAP[i]; return DOLAP[0]; }
  function giydir() {
    var o = kiyafetBul(K.k);
    if (ENIYI < o.kilit) { o = DOLAP[0]; K.k = o.id; }     // kilitliyse klasiğe dön
    B.m.tisort.color.setHex(o.tisort); B.m.tisort.emissive.setHex(o.emis); B.m.tisort.emissiveIntensity = o.emis ? 1 : 0;
    B.m.onluk.color.setHex(o.onluk); B.m.sapka.color.setHex(o.sapkaR);
    if (B.m.bere) B.m.bere.color.setHex(o.sapkaR);
    B.baskiTex.userData.ayar(o.baskiZ, o.baskiR);
    var sapkalar = B.sapkalar; for (var k in sapkalar) sapkalar[k].visible = (k === o.sapka);
    B.atki.visible = !!o.atki; if (o.atki) B.m.atki.color.setHex(o.atki);
    B.m.ten.color.setHex(TENLER[K.ten]);
    B.gozluk.visible = K.gozluk; B.kulaklik.visible = K.kulaklik;
    B.kulaklik.position.y = o.sapka === 'kasket' ? 0.15 : (o.sapka === 'tac' ? 0.1 : 0.2);
  }

  var elDolap = $('kosu-dolap'), dolapDon = 0;
  function dolapKur() {
    var lk = $('kd-kiyafet'), ln = $('kd-ten'), la = $('kd-aks');
    lk.innerHTML = ''; ln.innerHTML = ''; la.innerHTML = '';
    DOLAP.forEach(function (o) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'kd-kart'; b.dataset.id = o.id;
      var acik = ENIYI >= o.kilit;
      var hex = function (n) { return '#' + ('000000' + n.toString(16)).slice(-6); };
      b.innerHTML = '<span class="kd-ornek"><i style="background:' + hex(o.tisort) + '"></i><i style="background:' + hex(o.onluk) + '"></i><i style="background:' + hex(o.sapkaR) + '"></i></span>' +
        '<span class="kd-ad">' + o.ad + '</span><span class="kd-alt">' + (acik ? (K.k === o.id ? 'Giyiyor' : 'Seç') : '🔒 ' + o.kilit + ' puan') + '</span>';
      b.disabled = !acik; b.setAttribute('aria-pressed', K.k === o.id ? 'true' : 'false');
      b.addEventListener('click', function () { K.k = o.id; dolapKaydet(); giydir(); dolapKur(); bip(520, 0.08, 'triangle', 0.06, 760); });
      lk.appendChild(b);
    });
    TENLER.forEach(function (c, i) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'kd-nokta'; b.style.background = '#' + ('000000' + c.toString(16)).slice(-6);
      b.setAttribute('aria-label', 'Ten: ' + TEN_AD[i]); b.setAttribute('aria-pressed', K.ten === i ? 'true' : 'false');
      b.addEventListener('click', function () { K.ten = i; dolapKaydet(); giydir(); dolapKur(); });
      ln.appendChild(b);
    });
    [['gozluk', 'Güneş gözlüğü'], ['kulaklik', 'Kulaklık']].forEach(function (a) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'kd-cip'; b.textContent = a[1];
      b.setAttribute('aria-pressed', K[a[0]] ? 'true' : 'false');
      b.addEventListener('click', function () { K[a[0]] = !K[a[0]]; dolapKaydet(); giydir(); dolapKur(); });
      la.appendChild(b);
    });
  }

  /* =====================================================================
     ENGEL PROTOTİPLERİ (hepsinde Geek logosu)
     ===================================================================== */
  var PROTO = {};
  function protoKur() {
    var beyaz = std(0xffffff, { roughness: 0.35 }), laci = std(LACI, { roughness: 0.55 }), krem = std(KREMA, { roughness: 0.45 });
    var kahve = std(0x5b3317, { roughness: 0.35 });
    function decal(w, h, zemin, oran) {
      return new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ map: logoTexture(zemin, 512, Math.round(512 * h / w), oran), toneMapped: false }));
    }
    var f = new T.Group();
    f.add(mesh(new T.CylinderGeometry(0.95, 0.75, 0.1, 32), krem, 0, 0.05, 0));
    f.add(mesh(new T.CylinderGeometry(0.72, 0.5, 0.78, 32), beyaz, 0, 0.49, 0));
    f.add(mesh(new T.CylinderGeometry(0.64, 0.64, 0.03, 32), kahve, 0, 0.87, 0));
    var kenarK = mesh(new T.TorusGeometry(0.34, 0.035, 8, 32), std(0xd9a65a, { roughness: 0.2 }), 0, 0.875, 0); kenarK.rotation.x = Math.PI / 2; f.add(kenarK);
    f.add(mesh(new T.TorusGeometry(0.22, 0.06, 10, 22), beyaz, 0.78, 0.5, 0));
    var d1 = decal(0.78, 0.4, '#ffffff', 0.9); d1.position.set(0, 0.5, 0.64); d1.rotation.x = -0.08; f.add(d1);
    f.userData = { y0: 0, y1: 0.95 }; PROTO.fincan = golgeli(f, true, false);

    var b = new T.Group();
    b.add(mesh(new T.CylinderGeometry(0.78, 0.55, 2.2, 32), beyaz, 0, 1.1, 0));
    b.add(mesh(new T.CylinderGeometry(0.86, 0.82, 0.22, 32), laci, 0, 2.3, 0));
    b.add(mesh(new T.CylinderGeometry(0.62, 0.86, 0.14, 32), laci, 0, 2.48, 0));
    b.add(mesh(new T.CylinderGeometry(0.2, 0.2, 0.1, 16), laci, 0, 2.6, 0));
    b.add(mesh(new T.CylinderGeometry(0.71, 0.63, 0.9, 32, 1, true), krem, 0, 1.0, 0));
    var d2 = decal(1.1, 0.62, '#ffffff', 0.92); d2.position.set(0, 1.18, 0.78); b.add(d2);
    b.userData = { y0: 0, y1: 2.6 }; PROTO.bardak = golgeli(b, true, false);

    var g = new T.Group();
    g.add(mesh(new T.CylinderGeometry(0.85, 0.8, 0.22, 28), std(0xe0a24e), 0, 0.11, 0));
    g.add(mesh(new T.CylinderGeometry(0.88, 0.88, 0.2, 28), std(0x6b3418), 0, 0.32, 0));
    var peynir = mesh(new T.BoxGeometry(1.5, 0.05, 1.5), std(0xffc93a), 0, 0.46, 0); peynir.rotation.y = Math.PI / 4; g.add(peynir);
    var marul = mesh(new T.TorusGeometry(0.82, 0.1, 8, 28), std(0x4fb04f), 0, 0.52, 0); marul.rotation.x = Math.PI / 2; marul.scale.z = 0.6; g.add(marul);
    var ustE = mesh(new T.SphereGeometry(0.88, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2), std(0xe0a24e, { roughness: 0.4 }), 0, 0.55, 0); ustE.scale.y = 0.85; g.add(ustE);
    for (var i = 0; i < 10; i++) {
      var su = mesh(new T.SphereGeometry(0.05, 6, 4), std(0xfff4d6), 0, 0, 0); su.scale.y = 0.5;
      var aa = i * 0.7, rr = 0.2 + (i % 3) * 0.2; su.position.set(Math.cos(aa) * rr, 1.18 - rr * 0.38, Math.sin(aa) * rr + 0.1); g.add(su);
    }
    var bayrak = decal(0.62, 0.36, '#ffffff', 0.9); bayrak.position.set(0.3, 1.55, 0.35); g.add(bayrak);
    g.add(mesh(new T.CylinderGeometry(0.02, 0.02, 0.95, 6), laci, 0.0, 1.0, 0.3));
    g.userData = { y0: 0, y1: 1.35 }; PROTO.burger = golgeli(g, true, false);

    var k = new T.Group();
    var kr = mesh(new T.TorusGeometry(0.6, 0.3, 14, 28, Math.PI * 1.1), std(0xd9923c, { roughness: 0.7 }), 0, 0.32, 0);
    kr.rotation.set(-Math.PI / 2, 0, Math.PI * 0.95); kr.scale.set(1.15, 1, 1); k.add(kr);
    for (var j = 0; j < 4; j++) { var ban = mesh(new T.TorusGeometry(0.31, 0.03, 6, 14), std(0xa8681f), -0.55 + j * 0.37, 0.34, -0.35 + (j % 2) * 0.05); ban.rotation.y = Math.PI / 2; k.add(ban); }
    var d3 = decal(0.7, 0.34, '#ffffff', 0.9); d3.position.set(0, 0.2, 0.72); k.add(d3);
    k.userData = { y0: 0, y1: 0.95 }; PROTO.kruvasan = golgeli(k, true, false);

    var dn = new T.Group();
    var halka = mesh(new T.TorusGeometry(0.62, 0.3, 16, 32), std(0xe9b66e, { roughness: 0.6 }), 0, 0.5, 0); halka.rotation.x = Math.PI / 2 - 0.35; dn.add(halka);
    var krema = mesh(new T.TorusGeometry(0.62, 0.31, 16, 32, Math.PI * 2), std(0xff7fb0, { roughness: 0.25 }), 0, 0.57, 0); krema.rotation.x = Math.PI / 2 - 0.35; krema.scale.set(1, 1, 0.55); dn.add(krema);
    var renkler = [0xffffff, 0xffe066, 0x66c2ff, 0x7ed957];
    for (var q = 0; q < 14; q++) { var sp = mesh(new T.BoxGeometry(0.1, 0.03, 0.03), std(renkler[q % 4]), Math.cos(q * 0.9) * 0.6, 0.78 + Math.sin(q * 0.9) * 0.1, Math.sin(q * 0.9) * 0.45); sp.rotation.y = q; dn.add(sp); }
    var d6 = decal(0.6, 0.3, '#ffffff', 0.9); d6.position.set(0, 0.22, 0.85); dn.add(d6);
    dn.userData = { y0: 0, y1: 1.0 }; PROTO.donut = golgeli(dn, true, false);

    var m = new T.Group();
    m.add(mesh(new T.BoxGeometry(1.7, 2.1, 1.3), std(0xc9d0de, { roughness: 0.4, metalness: 0.25 }), 0, 1.05, 0));
    m.add(mesh(new T.BoxGeometry(1.8, 0.2, 1.4), laci, 0, 2.2, 0));
    var pano = decal(1.4, 0.7, '#ffffff', 0.88); pano.position.set(0, 1.55, 0.66); m.add(pano);
    m.add(mesh(new T.SphereGeometry(0.1, 10, 8), std(0xe0554b, { emissive: 0x801010 }), 0.55, 0.95, 0.66));
    var kolu = mesh(new T.CylinderGeometry(0.09, 0.09, 0.5, 10), laci, -0.3, 0.75, 0.85); kolu.rotation.x = Math.PI / 2; m.add(kolu);
    m.add(mesh(new T.CylinderGeometry(0.2, 0.2, 0.3, 16), beyaz, -0.3, 0.45, 0.85));
    m.userData = { y0: 0, y1: 2.35 }; PROTO.makine = golgeli(m, true, false);

    var p = new T.Group();
    var dir1 = mesh(new T.CylinderGeometry(0.1, 0.12, 3.3, 12), laci, -1.6 * SERIT, 1.65, 0); p.add(dir1);
    var dir2 = dir1.clone(); dir2.position.x = 1.6 * SERIT; p.add(dir2);
    var bez = mesh(new T.PlaneGeometry(3.3 * SERIT, 1.15), new T.MeshBasicMaterial({ map: logoTexture('#ffe9bd', 1024, 360, 0.62), side: T.DoubleSide, toneMapped: false }), 0, 2.1, 0); p.add(bez);
    p.add(mesh(new T.BoxGeometry(3.4 * SERIT, 0.09, 0.12), krem, 0, 1.5, 0));
    p.add(mesh(new T.BoxGeometry(3.4 * SERIT, 0.09, 0.12), krem, 0, 2.7, 0));
    p.userData = { y0: 1.45, y1: 3.0, tum: true }; PROTO.pankart = golgeli(p, true, false);

    var cek = new T.Group();
    var ck = mesh(new T.SphereGeometry(0.28, 16, 12), std(0x6b3a1c, { roughness: 0.3, emissive: 0x3a1a05, emissiveIntensity: 0.6 })); ck.scale.set(0.72, 1, 0.55); cek.add(ck);
    var ciz = mesh(new T.TorusGeometry(0.2, 0.025, 6, 14, Math.PI), std(KREMA, { emissive: 0x7a5200, emissiveIntensity: 0.8 }), 0, 0, 0.15); ciz.rotation.z = Math.PI / 2; ciz.scale.set(0.6, 1.1, 1); cek.add(ciz);
    cek.add(parlama(0xffc766, 1.25, 0.55));
    PROTO.cekirdek = cek;

    var e = new T.Group();
    e.add(mesh(new T.CylinderGeometry(0.32, 0.22, 0.42, 22), std(0xffffff, { emissive: 0x777777 })));
    e.add(mesh(new T.CylinderGeometry(0.42, 0.34, 0.06, 22), std(KREMA, { emissive: 0x7a5200 }), 0, -0.24, 0));
    e.add(mesh(new T.CylinderGeometry(0.27, 0.27, 0.03, 22), std(0x6b3a1c, { emissive: 0x3a1a05 }), 0, 0.21, 0));
    var hl = mesh(new T.TorusGeometry(0.62, 0.035, 8, 32), new T.MeshBasicMaterial({ color: 0xffd36a }), 0, 0, 0); hl.rotation.x = Math.PI / 2; e.add(hl);
    e.add(parlama(0xffd36a, 2.4, 0.7));
    PROTO.guc = e;

    // Cold Brew: buzlu cam bardak (zamanı yavaşlatır)
    var sg = new T.Group();
    sg.add(mesh(new T.CylinderGeometry(0.3, 0.24, 0.66, 22), new T.MeshStandardMaterial({ color: 0xa8dcff, transparent: true, opacity: 0.5, roughness: 0.08, emissive: 0x2a6fb0, emissiveIntensity: 0.6, depthWrite: false })));
    sg.add(mesh(new T.CylinderGeometry(0.265, 0.215, 0.4, 18), std(0x23160d, { roughness: 0.25, emissive: 0x143055, emissiveIntensity: 0.5 }), 0, -0.1, 0));
    [[-0.09, 0.22, 0.04, 0.4], [0.1, 0.2, -0.05, 0.9], [0.0, 0.27, 0.1, 1.5]].forEach(function (b) {
      var bz = mesh(new T.BoxGeometry(0.15, 0.15, 0.15), new T.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.75, roughness: 0.1, emissive: 0x9fd4ff, emissiveIntensity: 0.5 }), b[0], b[1], b[2]);
      bz.rotation.set(b[3], b[3] * 0.7, b[3] * 0.3); sg.add(bz);
    });
    var pipet = mesh(new T.CylinderGeometry(0.025, 0.025, 0.7, 8), std(0xe0554b, { emissive: 0x501010 }), 0.08, 0.45, 0); pipet.rotation.z = -0.22; sg.add(pipet);
    var sgHalka = mesh(new T.TorusGeometry(0.62, 0.03, 8, 32), new T.MeshBasicMaterial({ color: 0x8fd0ff }), 0, 0, 0); sgHalka.rotation.x = Math.PI / 2; sg.add(sgHalka);
    sg.add(parlama(0x6fc3ff, 2.5, 0.75));
    PROTO.soguk = sg;

    // Mıknatıs: nal mıknatıs (çekirdekleri çeker)
    var mk = new T.Group();
    var yay = mesh(new T.TorusGeometry(0.3, 0.11, 14, 28, Math.PI), std(0xe0554b, { roughness: 0.35, emissive: 0x6a1010, emissiveIntensity: 0.7 }), 0, 0.08, 0);
    mk.add(yay);
    [-1, 1].forEach(function (sx) {
      mk.add(mesh(new T.CylinderGeometry(0.11, 0.11, 0.34, 14), std(0xe0554b, { roughness: 0.35, emissive: 0x6a1010, emissiveIntensity: 0.7 }), sx * 0.3, -0.09, 0));
      mk.add(mesh(new T.CylinderGeometry(0.115, 0.115, 0.14, 14), std(0xe6edf8, { roughness: 0.2, metalness: 0.2, emissive: 0x556070, emissiveIntensity: 0.6 }), sx * 0.3, -0.33, 0));
    });
    mk.add(parlama(0xff8a6a, 2.3, 0.7));
    mk.rotation.z = 0.0;
    PROTO.mikn = mk;
  }

  /* =====================================================================
     DÜNYA
     ===================================================================== */
  function pencereDoku() {
    var cv = document.createElement('canvas'); cv.width = 128; cv.height = 128;
    var c = cv.getContext('2d'); c.fillStyle = '#fff'; c.fillRect(0, 0, 128, 128);
    var em = document.createElement('canvas'); em.width = 128; em.height = 128;
    var e = em.getContext('2d'); e.fillStyle = '#000'; e.fillRect(0, 0, 128, 128);
    for (var y = 0; y < 4; y++) for (var x = 0; x < 3; x++) {
      var px = 12 + x * 38, py = 10 + y * 30;
      c.fillStyle = '#5f78a8'; c.fillRect(px, py, 24, 20);
      c.fillStyle = 'rgba(255,255,255,.5)'; c.fillRect(px, py, 24, 5);
      c.fillStyle = 'rgba(0,0,0,.12)'; c.fillRect(px - 3, py + 21, 30, 3);
      if ((x * 7 + y * 13 + (x * y)) % 3 !== 0) { e.fillStyle = '#fff'; e.fillRect(px, py, 24, 20); }
    }
    var t1 = srgb(new T.CanvasTexture(c.canvas)), t2 = srgb(new T.CanvasTexture(em));
    [t1, t2].forEach(function (t) { t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 4; });
    return [t1, t2];
  }
  function yolDokusu() {
    var cv = document.createElement('canvas'); cv.width = 256; cv.height = 256;
    var c = cv.getContext('2d');
    c.fillStyle = '#2b2f58'; c.fillRect(0, 0, 256, 256);
    for (var k = 0; k < 400; k++) { c.fillStyle = 'rgba(255,255,255,' + (Math.random() * 0.05) + ')'; c.fillRect(Math.random() * 256, Math.random() * 256, 2, 2); }
    for (var k2 = 0; k2 < 200; k2++) { c.fillStyle = 'rgba(0,0,0,' + (Math.random() * 0.08) + ')'; c.fillRect(Math.random() * 256, Math.random() * 256, 3, 3); }
    c.fillStyle = '#f2b544';
    var w = 256 / 3;
    for (var i = 1; i < 3; i++) { c.fillRect(i * w - 3, 20, 6, 90); c.fillRect(i * w - 3, 148, 6, 90); }
    var t = srgb(new T.CanvasTexture(cv)); t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 8;
    t.repeat.set(1, 18);
    return t;
  }
  function ufukDokusu() {
    var cv = document.createElement('canvas'); cv.width = 1024; cv.height = 128;
    var c = cv.getContext('2d'); c.fillStyle = '#fff';
    var x = 0;
    while (x < 1024) { var w = 24 + Math.random() * 50, h = 30 + Math.random() * 90; c.fillRect(x, 128 - h, w, h); if (Math.random() < 0.4) c.fillRect(x + w / 2 - 2, 128 - h - 14, 4, 14); x += w + Math.random() * 6; }
    var t = srgb(new T.CanvasTexture(cv)); t.wrapS = T.RepeatWrapping; t.repeat.x = 2; return t;
  }
  function caprazTexture() {
    var cv = document.createElement('canvas'); cv.width = 256; cv.height = 64;
    var c = cv.getContext('2d'); c.fillStyle = 'rgba(255,255,255,.88)';
    for (var i = 0; i < 12; i++) c.fillRect(8 + i * 20, 0, 12, 64);
    return srgb(new T.CanvasTexture(cv));
  }
  function neonDokusu(metin, renk) {
    var cv = document.createElement('canvas'); cv.width = 384; cv.height = 150;
    var c = cv.getContext('2d');
    c.textAlign = 'center'; c.textBaseline = 'middle'; c.font = '800 88px system-ui,sans-serif';
    c.strokeStyle = renk; c.lineWidth = 7; c.lineJoin = 'round';
    c.shadowColor = renk; c.shadowBlur = 26; c.strokeText(metin, 192, 78);
    c.shadowBlur = 8; c.strokeText(metin, 192, 78);
    c.shadowBlur = 0; c.fillStyle = '#ffffff'; c.globalAlpha = 0.85; c.fillText(metin, 192, 78);
    return srgb(new T.CanvasTexture(cv));
  }
  function bayrakGirland() {
    // yolun iki yanındaki direkler arasında sarkan Geek flamaları
    var n = 16, xs = SERIT * 1.5 + 1.0 - 0.45, poz = [], col = [];
    var renkler = [new T.Color(KREMA), new T.Color(MAVI), new T.Color(0xffffff), new T.Color(0xe0554b)];
    function egri(t) { var x = -xs + 2 * xs * t; return [x, 7.5 - Math.sin(t * Math.PI) * 0.9]; }
    for (var i = 0; i < n; i++) {
      var a = egri(i / n), b = egri((i + 1) / n), m = egri((i + 0.5) / n), r = renkler[i % 4];
      poz.push(a[0], a[1], 0, b[0], b[1], 0, m[0], m[1] - 0.62, 0);
      for (var q = 0; q < 3; q++) col.push(r.r, r.g, r.b);
    }
    var g = new T.BufferGeometry();
    g.setAttribute('position', new T.Float32BufferAttribute(poz, 3)); g.setAttribute('color', new T.Float32BufferAttribute(col, 3));
    var m2 = mesh(g, new T.MeshBasicMaterial({ vertexColors: true, side: T.DoubleSide }));
    var grup = new T.Group(); grup.add(m2);
    var direkM = std(0x2b2f45, { roughness: 0.5, metalness: 0.4 });
    [-1, 1].forEach(function (yy) { grup.add(mesh(new T.CylinderGeometry(0.06, 0.09, 7.6, 8), direkM, yy * (xs + 0.1), 3.8, 0)); });
    var ip = mesh(new T.BoxGeometry(2 * xs, 0.025, 0.025), direkM, 0, 7.5, 0); ip.visible = false; grup.add(ip);
    return grup;
  }

  var BINA_RENK = [0xfff1d6, 0xf6d7b0, 0xd9e4f5, 0xe9b8a0, 0xcfd6ea];
  function kayanEkle(g, z, boy) { dunya.kayan.push({ g: g, z: z, boy: boy }); g.position.z = z; }

  function dunyaKur() {
    dunya.kayan = [];
    var pen = pencereDoku();
    dunya.binaMat = BINA_RENK.map(function (r) {
      return std(r, { map: pen[0], emissiveMap: pen[1], emissive: 0xffc860, emissiveIntensity: 0, roughness: 0.85 });
    });
    // yol
    dunya.yolDoku = yolDokusu();
    var yol = mesh(new T.PlaneGeometry(SERIT * 3, 420), std(0xffffff, { map: dunya.yolDoku, roughness: 0.82 }), 0, 0, -160);
    yol.rotation.x = -Math.PI / 2; yol.receiveShadow = true; scene.add(yol); dunya.yolMat = yol.material;
    var kaldirimM = std(0xb8ae96, { roughness: 0.9 });
    [-1, 1].forEach(function (y) {
      var k = mesh(new T.BoxGeometry(5.5, 0.25, 420), kaldirimM, y * (SERIT * 1.5 + 2.9), -0.05, -160); k.receiveShadow = true; scene.add(k);
      var bordur = mesh(new T.BoxGeometry(0.3, 0.32, 420), std(0x9aa0b4), y * (SERIT * 1.5 + 0.1), 0.02, -160); bordur.receiveShadow = true; scene.add(bordur);
    });
    dunya.zemin = mesh(new T.PlaneGeometry(300, 420), std(0x6f7a5a, { roughness: 1 }), 0, -0.2, -160);
    dunya.zemin.rotation.x = -Math.PI / 2; scene.add(dunya.zemin);

    // yol üstü: yaya geçidi + yola boyalı Geek logosu (kayar)
    var capraz = srgb(caprazTexture());
    var gecitM = new T.MeshBasicMaterial({ map: capraz, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
    [-60, -210].forEach(function (z) {
      var gz = mesh(new T.PlaneGeometry(SERIT * 3, 3.2), gecitM); gz.rotation.x = -Math.PI / 2; gz.position.y = 0.02; scene.add(gz); kayanEkle(gz, z, 300);
    });
    var logoYol = new T.MeshBasicMaterial({ map: logoTexture(null, 512, 256, 0.92, '#f2b544'), transparent: true, opacity: 0.85, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, toneMapped: false });
    [-135, -285].forEach(function (z) {
      var lz = mesh(new T.PlaneGeometry(SERIT * 2.4, SERIT * 1.2), logoYol); lz.rotation.x = -Math.PI / 2; lz.position.y = 0.022; scene.add(lz); kayanEkle(lz, z, 300);
    });

    // neon tabela dokuları
    dunya.neonMat = [['OPEN', '#ff4fa3'], ['CAFE', '#38f2ff'], ['KAHVE', '#ffb347'], ['GEEK', '#9d7bff']].map(function (n) {
      return new T.MeshBasicMaterial({ map: neonDokusu(n[0], n[1]), transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false });
    });
    // binalar
    dunya.binalar = [];
    var BAS = 260, adet = 15, adim = BAS / adet;
    var sablon = [[5, 9], [6, 14], [5, 6], [7, 11], [6, 8]];
    var camM = std(0x4d6fa3, { roughness: 0.12, metalness: 0.3, emissive: 0xffb860, emissiveIntensity: 0.35 });
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < adet; i++) {
        var grup = new T.Group();
        var s = sablon[(i * 3 + (yon > 0 ? 1 : 0)) % sablon.length];
        var gen = s[0], yuk = s[1], der = 8;
        var geo = new T.BoxGeometry(gen, yuk, der);
        var uv = geo.attributes.uv; for (var q = 0; q < uv.count; q++) uv.setXY(q, uv.getX(q) * gen / 2.4, uv.getY(q) * yuk / 3.2);
        var m = mesh(geo, dunya.binaMat[(i + (yon > 0 ? 2 : 0)) % dunya.binaMat.length], 0, yuk / 2, 0); grup.add(m);
        grup.add(mesh(new T.BoxGeometry(gen + 0.3, 0.3, der + 0.3), std(0x8c7b6b), 0, yuk + 0.1, 0));
        // çatı detayları
        var tank = mesh(new T.CylinderGeometry(0.6, 0.6, 1.0, 12), std(0x8a8f9c), (i % 2 ? 1 : -1) * 1.1, yuk + 0.75, 1.5); grup.add(tank);
        grup.add(mesh(new T.BoxGeometry(1.2, 0.7, 1.0), std(0xa7acb8), (i % 2 ? -1 : 1) * 1.0, yuk + 0.55, -1.8));
        // zemin kat vitrini + tabela + tente
        var vitrin = mesh(new T.PlaneGeometry(der * 0.7, 2.2), camM); vitrin.position.set(-yon * (gen / 2 + 0.03), 1.3, 0); vitrin.rotation.y = -yon * Math.PI / 2; grup.add(vitrin);
        if (i % 3 === 1) {            // neon tabela (geceleri parlar)
          var nm = dunya.neonMat[(i + (yon > 0 ? 1 : 0)) % dunya.neonMat.length];
          var neon = mesh(new T.PlaneGeometry(3.4, 1.3), nm, -yon * (gen / 2 + 0.1), 5.6 + (i % 2) * 1.2, (i % 2 ? 1.3 : -1.2));
          neon.rotation.y = -yon * Math.PI / 2; grup.add(neon);
        }
        if (i % 2 === 0) {
          var tabela = mesh(new T.PlaneGeometry(3.6, 1.6), new T.MeshBasicMaterial({ map: logoTexture('#ffffff', 512, 228, 0.82), toneMapped: false }), -yon * (gen / 2 + 0.06), 3.7, 0);
          tabela.rotation.y = -yon * Math.PI / 2; grup.add(tabela);
          var tente = mesh(new T.BoxGeometry(1.2, 0.12, der * 0.78), std(i % 4 === 0 ? 0xe0554b : KREMA), -yon * (gen / 2 + 0.6), 2.65, 0); tente.rotation.z = yon * 0.22; grup.add(tente);
        }
        grup.position.set(yon * (SERIT * 1.5 + 8.2 + gen / 2 + (i % 3) * 0.8), 0, -i * adim);
        scene.add(grup);
        dunya.binalar.push({ g: grup, z: -i * adim });
      }
    });
    dunya.binaBoy = BAS;

    // lambalar + flama girlandları
    dunya.lambalar = [];
    var lampM = std(0x2b2f45, { roughness: 0.5, metalness: 0.4 });
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < 14; i++) {
        var g = new T.Group();
        g.add(mesh(new T.CylinderGeometry(0.07, 0.1, 4.4, 10), lampM, 0, 2.2, 0));
        g.add(mesh(new T.BoxGeometry(1.1, 0.08, 0.08), lampM, -yon * 0.55, 4.4, 0));
        var amp = mesh(new T.SphereGeometry(0.2, 12, 10), new T.MeshBasicMaterial({ color: 0xffe2a0, transparent: true, opacity: 0.4 }), -yon * 1.05, 4.3, 0); g.add(amp);
        var pr = parlama(0xffd27a, 2.0, 0.0); pr.position.set(-yon * 1.05, 4.3, 0); g.add(pr);
        if (!glowTex) glowTex = parlamaDokusu();
        var havuz = mesh(new T.PlaneGeometry(7, 7), new T.MeshBasicMaterial({ map: glowTex, color: 0xffd27a, transparent: true, opacity: 0, blending: T.AdditiveBlending, depthWrite: false }), -yon * 3.0, 0.04, 0);
        havuz.rotation.x = -Math.PI / 2; g.add(havuz);
        g.position.set(yon * (SERIT * 1.5 + 0.9), 0, -i * 19);
        scene.add(g); dunya.lambalar.push({ g: g, z: -i * 19, amp: amp, pr: pr, havuz: havuz });
        if (yon === 1 && i % 2 === 0) {
          var gr = bayrakGirland(); scene.add(gr); kayanEkle(gr, -i * 19, 266);
        }
      }
    });
    dunya.lambaBoy = 14 * 19;

    // ağaçlar
    dunya.agaclar = [];
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < 8; i++) {
        var g = new T.Group();
        g.add(mesh(new T.CylinderGeometry(0.14, 0.2, 1.7, 8), std(0x6b4a2b), 0, 0.85, 0));
        var y1 = mesh(new T.SphereGeometry(0.85, 14, 12), std(0x4f9a52, { roughness: 0.9 }), 0, 2.3, 0); y1.scale.y = 1.1; g.add(y1);
        g.add(mesh(new T.SphereGeometry(0.6, 12, 10), std(0x5fb060, { roughness: 0.9 }), 0.4, 2.9, 0.2));
        golgeli(g, true, false);
        g.position.set(yon * (SERIT * 1.5 + 2.4), 0, -i * 33 - 10);
        scene.add(g); dunya.agaclar.push({ g: g, z: -i * 33 - 10 });
      }
    });
    dunya.agacBoy = 8 * 33;

    // kaldırım mobilyaları: bank, babalı kazık, çöp kutusu
    dunya.props = [];
    var yesilM = std(0x2f6b4f, { roughness: 0.7 }), ahsap = std(0x9b6a3f, { roughness: 0.8 }), demir = std(0x2b2f45, { roughness: 0.5, metalness: 0.4 });
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < 7; i++) {
        var g = new T.Group(), tip = (i + (yon > 0 ? 1 : 0)) % 3;
        if (tip === 0) {
          g.add(mesh(new T.BoxGeometry(1.6, 0.08, 0.5), ahsap, 0, 0.5, 0));
          g.add(mesh(new T.BoxGeometry(1.6, 0.45, 0.07), ahsap, 0, 0.82, -yon * 0.22));
          [-0.7, 0.7].forEach(function (bx) { g.add(mesh(new T.BoxGeometry(0.07, 0.5, 0.45), demir, bx, 0.25, 0)); });
          g.rotation.y = yon * Math.PI / 2;
        } else if (tip === 1) {
          g.add(mesh(new T.CylinderGeometry(0.11, 0.13, 0.75, 12), demir, 0, 0.38, 0));
          g.add(mesh(new T.CylinderGeometry(0.115, 0.115, 0.08, 12), std(0xf2b544, { emissive: 0x3a2800, emissiveIntensity: 0.5 }), 0, 0.62, 0));
        } else {
          g.add(mesh(new T.CylinderGeometry(0.28, 0.24, 0.8, 14), yesilM, 0, 0.4, 0));
          g.add(mesh(new T.CylinderGeometry(0.3, 0.3, 0.07, 14), demir, 0, 0.82, 0));
          var bz = mesh(new T.PlaneGeometry(0.3, 0.14), new T.MeshBasicMaterial({ map: logoTexture('#ffffff', 192, 90, 0.9), toneMapped: false }), 0, 0.45, 0.285); g.add(bz);
        }
        golgeli(g, true, false);
        g.position.set(yon * (SERIT * 1.5 + 3.9 + (tip === 0 ? 0.6 : 0)), 0.05, -i * 37 - 5);
        scene.add(g); dunya.props.push({ g: g, z: -i * 37 - 5 });
      }
    });
    dunya.propBoy = 7 * 37;

    // kaldırım kafe takımları (Geek şemsiyeli)
    dunya.masalar = [];
    var semsiyeA = std(KREMA, { roughness: 0.7, side: T.DoubleSide }), semsiyeB = std(0xffffff, { roughness: 0.7, side: T.DoubleSide });
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < 6; i++) {
        var g = new T.Group();
        g.add(mesh(new T.CylinderGeometry(0.04, 0.04, 2.2, 8), lampM, 0, 1.1, 0));
        var cati = mesh(new T.ConeGeometry(1.25, 0.55, 12, 1, true), i % 2 ? semsiyeA : semsiyeB, 0, 2.3, 0); g.add(cati);
        var lg = mesh(new T.PlaneGeometry(0.9, 0.4), new T.MeshBasicMaterial({ map: logoTexture('#ffffff', 256, 112, 0.92), toneMapped: false }), 0, 2.0, 0.86); lg.rotation.x = -0.55; g.add(lg);
        g.add(mesh(new T.CylinderGeometry(0.5, 0.5, 0.06, 18), std(0x2b2f45), 0, 0.75, 0));
        g.add(mesh(new T.CylinderGeometry(0.05, 0.05, 0.75, 8), lampM, 0, 0.37, 0));
        [-1, 1].forEach(function (s) { g.add(mesh(new T.BoxGeometry(0.4, 0.06, 0.4), std(0xe0554b), s * 0.95, 0.5, 0.2)); g.add(mesh(new T.BoxGeometry(0.4, 0.4, 0.05), std(0xe0554b), s * 0.95, 0.72, 0.4)); });
        golgeli(g, true, false);
        g.position.set(yon * (SERIT * 1.5 + 4.4 + (i % 2) * 0.5), 0, -i * 41 - 22);
        scene.add(g); dunya.masalar.push({ g: g, z: -i * 41 - 22 });
      }
    });
    dunya.masaBoy = 6 * 41;

    // gökyüzü kubbesi, güneş, ay, yıldızlar, bulutlar, ufuk
    dunya.gokTop = new T.Color(0x6fb7f2); dunya.gokAlt = new T.Color(0xffe7b8);
    var gokMat = new T.ShaderMaterial({
      side: T.BackSide, depthWrite: false, fog: false,
      uniforms: { ust: { value: dunya.gokTop }, alt: { value: dunya.gokAlt } },
      vertexShader: 'varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 ust; uniform vec3 alt; varying vec3 vP; void main(){ float h = clamp(normalize(vP).y, 0.0, 1.0); vec3 c = mix(alt, ust, pow(h, 0.55)); gl_FragColor = vec4(c, 1.0); gl_FragColor = linearToOutputTexel(gl_FragColor); }'
    });
    dunya.gok = mesh(new T.SphereGeometry(300, 24, 16), gokMat); dunya.gok.renderOrder = -10; scene.add(dunya.gok);
    dunya.ufukMat = new T.MeshBasicMaterial({ map: ufukDokusu(), color: 0xe9c488, transparent: true, fog: false, depthWrite: false });
    var ufuk = mesh(new T.PlaneGeometry(520, 60), dunya.ufukMat, 0, 26, -230); scene.add(ufuk);
    dunya.gunes = mesh(new T.CircleGeometry(16, 40), new T.MeshBasicMaterial({ color: 0xfff1b8, fog: false, toneMapped: false }), 40, 40, -235); scene.add(dunya.gunes);
    dunya.gunesParla = parlama(0xffe9a8, 120, 0.45); dunya.gunesParla.position.set(40, 40, -233); scene.add(dunya.gunesParla); dunya.gunesParla.material.fog = false;
    dunya.ay = mesh(new T.CircleGeometry(8, 32), new T.MeshBasicMaterial({ color: 0xe8eeff, fog: false, toneMapped: false }), -50, 60, -236); scene.add(dunya.ay);
    var ys = new Float32Array(300 * 3);
    for (var s = 0; s < 300; s++) { ys[s * 3] = (Math.random() - 0.5) * 460; ys[s * 3 + 1] = 40 + Math.random() * 130; ys[s * 3 + 2] = -240; }
    var yg = new T.BufferGeometry(); yg.setAttribute('position', new T.BufferAttribute(ys, 3));
    dunya.yildiz = new T.Points(yg, new T.PointsMaterial({ color: 0xffffff, size: 1.8, sizeAttenuation: false, transparent: true, opacity: 0, fog: false }));
    scene.add(dunya.yildiz);
    dunya.bulutlar = [];
    var bd = bulutDokusu();
    for (var b = 0; b < 9; b++) {
      var sp = new T.Sprite(new T.SpriteMaterial({ map: bd, transparent: true, opacity: 0.8, depthWrite: false, fog: false }));
      var olc = 70 + Math.random() * 60; sp.scale.set(olc, olc / 2, 1);
      sp.position.set((Math.random() - 0.5) * 380, 55 + Math.random() * 45, -200 - Math.random() * 30);
      scene.add(sp); dunya.bulutlar.push(sp);
    }
    dunya.kuslar = [];
    var kusM = new T.MeshBasicMaterial({ color: 0x2b2f45, side: T.DoubleSide, fog: false });
    for (var ku = 0; ku < 7; ku++) {
      var kg = new T.Group(), kw = [];
      [-1, 1].forEach(function (sx) {
        var kn = new T.Group(); kn.add(mesh(new T.PlaneGeometry(1.5, 0.4), kusM, sx * 0.75, 0, 0)); kg.add(kn); kw.push(kn);
      });
      kg.position.set(-200 + Math.random() * 400, 22 + Math.random() * 26, -120 - Math.random() * 70);
      kg.scale.setScalar(0.9 + Math.random() * 0.6);
      scene.add(kg); dunya.kuslar.push({ g: kg, kanat: kw, hiz: 5 + Math.random() * 4, faz: Math.random() * 6 });
    }
  }

  var FAZ = {
    gun: { ust: new T.Color(0x5aa9ee), alt: new T.Color(0xffe3ad) },
    aksam: { ust: new T.Color(0x4a3f93), alt: new T.Color(0xff9a68) },
    gece: { ust: new T.Color(0x040720), alt: new T.Color(0x1b2660) }
  };
  var _a = new T.Color(), _b = new T.Color(), _c = new T.Color(), _d = new T.Color();
  var GRI_UST = new T.Color(0x56606f), GRI_ALT = new T.Color(0x9aa3b0);
  function gokGuncelle(mesafe, dt) {
    var faz = (mesafe / 2700) % 1;
    var A, Bk, t, gece;
    if (faz < 0.35) { A = FAZ.gun; Bk = FAZ.gun; t = 0; gece = 0; }
    else if (faz < 0.55) { A = FAZ.gun; Bk = FAZ.aksam; t = (faz - 0.35) / 0.2; gece = 0; }
    else if (faz < 0.7) { A = FAZ.aksam; Bk = FAZ.gece; t = (faz - 0.55) / 0.15; gece = t; }
    else if (faz < 0.85) { A = FAZ.gece; Bk = FAZ.gece; t = 0; gece = 1; }
    else { A = FAZ.gece; Bk = FAZ.gun; t = (faz - 0.85) / 0.15; gece = 1 - t; }
    _a.copy(A.ust).lerp(Bk.ust, t); _b.copy(A.alt).lerp(Bk.alt, t);
    var yag = G ? G.yagmur : 0, isl = G ? G.islak : 0;
    if (yag > 0.001) { _a.lerp(GRI_UST, yag * 0.6); _b.lerp(GRI_ALT, yag * 0.55); }
    dunya.gece = gece;
    dunya.gokTop.copy(_a); dunya.gokAlt.copy(_b);
    scene.fog.color.copy(_b); renderer.setClearColor(_b);
    hemi.intensity = (0.95 - gece * 0.6) * (1 - yag * 0.18); gunes.intensity = (1.5 - gece * 1.15) * (1 - yag * 0.55); dolgu.intensity = 0.35 + gece * 0.25;
    hemi.color.copy(_a).lerp(_c.setHex(0xffffff), 0.5);
    dunya.binaMat.forEach(function (m) { m.emissiveIntensity = gece * 0.95; });
    dunya.lambalar.forEach(function (l) {
      var gecem = Math.min(1, gece + yag * 0.45);
      l.amp.material.opacity = 0.4 + gecem * 0.6; l.pr.material.opacity = gecem * 0.7;
      l.havuz.material.opacity = Math.min(0.85, gecem * 0.5 + isl * 0.22);
    });
    dunya.neonMat.forEach(function (m) { m.opacity = 0.45 + Math.min(1, gece + yag * 0.4) * 0.55; });
    dunya.yolMat.roughness = 0.82 - 0.52 * isl; dunya.yolMat.metalness = 0.18 * isl; dunya.yolMat.color.setScalar(1 - 0.28 * isl);
    dunya.ufukMat.color.copy(_b).multiplyScalar(0.7);
    dunya.gunes.position.y = 40 - gece * 75; dunya.gunesParla.position.y = dunya.gunes.position.y; dunya.gunesParla.material.opacity = 0.45 * (1 - gece);
    dunya.ay.position.y = 10 + gece * 52;
    dunya.yildiz.material.opacity = Math.max(0, gece - 0.3) * (1 - yag);
    dunya.kuslar.forEach(function (k) {
      k.g.visible = gece < 0.45 && yag < 0.3;
      if (!k.g.visible) return;
      k.faz += dt * 12; k.g.position.x += dt * k.hiz; if (k.g.position.x > 210) k.g.position.x = -210;
      k.kanat[0].rotation.z = Math.sin(k.faz) * 0.7; k.kanat[1].rotation.z = -Math.sin(k.faz) * 0.7;
    });
    dunya.zemin.material.color.setHex(0x6f7a5a).multiplyScalar(1 - gece * 0.6);
    dunya.bulutlar.forEach(function (b, i) {
      b.position.x += dt * (1.2 + i * 0.1); if (b.position.x > 220) b.position.x = -220;
      b.material.color.copy(_d.setHex(0xffffff).lerp(_c.setHex(gece > 0.5 ? 0x39406e : 0xffc9a8), Math.min(1, gece + (faz > 0.4 && faz < 0.7 ? 0.5 : 0))));
      b.material.opacity = 0.85 - gece * 0.5;
    });
    gunes.position.set(-8, 18, 4);
  }

  /* =====================================================================
     EFEKTLER: hız çizgileri, toz, parçacıklar
     ===================================================================== */
  function fxKur() {
    fx.cizgiler = [];
    var m = new T.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, blending: T.AdditiveBlending, depthWrite: false, fog: false });
    for (var i = 0; i < 26; i++) {
      var c = new T.Mesh(new T.BoxGeometry(0.03, 0.03, 4), m.clone());
      c.userData.z = -Math.random() * 40; c.userData.a = Math.random() * 6.28; c.userData.r = 3 + Math.random() * 6;
      scene.add(c); fx.cizgiler.push(c);
    }
    fx.toz = [];
    var tm = new T.SpriteMaterial({ map: parlamaDokusu(), color: 0xe8dfcf, transparent: true, opacity: 0, depthWrite: false });
    for (var j = 0; j < 22; j++) { var sp = new T.Sprite(tm.clone()); sp.visible = false; sp.userData = { omur: 0, v: new T.Vector3() }; scene.add(sp); fx.toz.push(sp); }
    fx.tozZaman = 0;
  }
  function tozAt(x, z) {
    var p = fx.toz.find(function (s) { return !s.visible; }); if (!p) return;
    p.visible = true; p.position.set(x + (Math.random() - 0.5) * 0.3, 0.12, z); p.userData.omur = 0.5; p.userData.v.set((Math.random() - 0.5) * 1.2, 0.8 + Math.random() * 0.6, 1.5);
    p.scale.setScalar(0.3);
  }
  function fxGuncelle(dt) {
    var hizOran = G && !G.ol && G.geri <= 0 ? Math.max(0, (G.hiz - 18) / 24) + (G.guc > 0 ? 0.5 : 0) : 0;
    fx.cizgiler.forEach(function (c) {
      c.userData.z += (G ? G.hiz : 8) * dt * 1.7;
      if (c.userData.z > 8) { c.userData.z = -50 - Math.random() * 20; c.userData.a = Math.random() * 6.28; c.userData.r = 3.2 + Math.random() * 6; }
      var cx = kamera.position.x + Math.cos(c.userData.a) * c.userData.r, cy = 2.6 + Math.sin(c.userData.a) * c.userData.r * 0.6;
      c.position.set(cx, Math.max(0.3, cy), c.userData.z);
      c.material.opacity = Math.min(0.5, hizOran * 0.55) * (1 - Math.max(0, (c.userData.z + 5) / 13));
      c.scale.z = 1 + hizOran * 2;
    });
    fx.toz.forEach(function (s) {
      if (!s.visible) return;
      s.userData.omur -= dt; if (s.userData.omur <= 0) { s.visible = false; return; }
      s.position.addScaledVector(s.userData.v, dt); s.scale.setScalar(0.3 + (0.5 - s.userData.omur) * 1.6);
      s.material.opacity = s.userData.omur * 0.7;
    });
  }

  function parcacikPatlat(x, y, z, renk, adet, hizz) {
    for (var i = 0; i < adet; i++) {
      var p = parcaciklar.find(function (q) { return !q.m.visible; });
      if (!p) { if (parcaciklar.length > 110) return; p = { m: new T.Mesh(new T.BoxGeometry(0.14, 0.14, 0.14), new T.MeshBasicMaterial({ color: 0xffffff })), v: new T.Vector3(), omur: 0 }; scene.add(p.m); parcaciklar.push(p); }
      p.m.visible = true; p.m.material.color.setHex(renk[i % renk.length]);
      p.m.position.set(x, y, z); p.v.set((Math.random() - 0.5) * hizz, Math.random() * hizz * 0.9 + 1, (Math.random() - 0.5) * hizz);
      p.omur = 0.55 + Math.random() * 0.45; p.m.scale.setScalar(1);
    }
  }
  function parcacikGuncelle(dt) {
    parcaciklar.forEach(function (p) {
      if (!p.m.visible) return;
      p.omur -= dt; if (p.omur <= 0) { p.m.visible = false; return; }
      p.v.y -= 22 * dt; p.m.position.addScaledVector(p.v, dt); p.m.scale.setScalar(Math.max(0.1, p.omur * 1.6));
      p.m.rotation.x += dt * 8; p.m.rotation.y += dt * 6;
    });
  }


  /* =====================================================================
     HAVA: yağmur, şimşek, ıslak yol, kahve buharı
     ===================================================================== */
  var hava = { n: 900, sesKaynak: null, sesGain: null, ilkMesaj: false };
  function havaKur() {
    var n = hava.n, pos = new Float32Array(n * 6);
    hava.x = new Float32Array(n); hava.y = new Float32Array(n); hava.z = new Float32Array(n); hava.v = new Float32Array(n);
    for (var i = 0; i < n; i++) {
      hava.x[i] = (Math.random() - 0.5) * 34; hava.y[i] = Math.random() * 18; hava.z[i] = -75 + Math.random() * 85; hava.v[i] = 26 + Math.random() * 12;
    }
    var geo = new T.BufferGeometry(); geo.setAttribute('position', new T.BufferAttribute(pos, 3));
    hava.mat = new T.LineBasicMaterial({ color: 0xcfe2ff, transparent: true, opacity: 0, depthWrite: false, fog: true });
    hava.cizgi = new T.LineSegments(geo, hava.mat); hava.cizgi.frustumCulled = false; hava.cizgi.visible = false; scene.add(hava.cizgi);
    // kahve buharı havuzu
    fx.buhar = [];
    var bm = new T.SpriteMaterial({ map: parlamaDokusu(), color: 0xffffff, transparent: true, opacity: 0, depthWrite: false });
    for (var b = 0; b < 12; b++) { var sp = new T.Sprite(bm.clone()); sp.visible = false; sp.userData = { omur: 0 }; scene.add(sp); fx.buhar.push(sp); }
    fx.buharSay = 0;
  }
  var _vp = new T.Vector3();
  function yagmurSesi(deger) {
    if (ses.kapali || !ses.ctx) { if (hava.sesGain) hava.sesGain.gain.value = 0; return; }
    if (!hava.sesKaynak) {
      try {
        var c = ses.ctx, n = c.sampleRate * 2, b = c.createBuffer(1, n, c.sampleRate), d = b.getChannelData(0);
        for (var i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
        var k = c.createBufferSource(); k.buffer = b; k.loop = true;
        var f = c.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 3200; f.Q.value = 0.6;
        var g = c.createGain(); g.gain.value = 0; k.connect(f); f.connect(g); g.connect(c.destination); k.start();
        hava.sesKaynak = k; hava.sesGain = g;
      } catch (e) { return; }
    }
    hava.sesGain.gain.value = deger * 0.05;
  }
  function havaGuncelle(dt, calisiyor) {
    if (!G) return;
    // yağmur takvimi: 1100 m'den sonra her 3600 m'de 1300 m boyunca
    var fz = (G.metre - 1100) % 3600;
    G.yagmurHedef = (calisiyor && G.metre > 1100 && fz < 1300) ? 1 : 0;
    if (G.yagmurHedef && G.yagmur < 0.02 && !hava.ilkMesaj) { hava.ilkMesaj = true; mesaj('Yağmur başladı · yol kaygan görünüyor', 2200); }
    if (!G.yagmurHedef) hava.ilkMesaj = G.yagmur > 0.02;
    G.yagmur += (G.yagmurHedef - G.yagmur) * Math.min(1, dt * 0.5);
    if (G.yagmur < 0.003 && !G.yagmurHedef) G.yagmur = 0;
    G.islak += (G.yagmur - G.islak) * Math.min(1, dt * (G.yagmur > G.islak ? 0.7 : 0.12));
    var y = G.yagmur;
    hava.cizgi.visible = y > 0.02; hava.mat.opacity = 0.42 * y;
    if (hava.cizgi.visible) {
      var p = hava.cizgi.geometry.attributes.position.array, n = hava.n, hz = G.hiz, kx = kamera.position.x;
      for (var i = 0; i < n; i++) {
        hava.y[i] -= hava.v[i] * dt; hava.z[i] += hz * dt * 0.9;
        if (hava.y[i] < 0) { hava.y[i] += 18; hava.x[i] = (Math.random() - 0.5) * 34; hava.z[i] = -75 + Math.random() * 85; }
        if (hava.z[i] > 10) hava.z[i] -= 85;
        var o = i * 6, x = hava.x[i] + kx * 0.5;
        p[o] = x; p[o + 1] = hava.y[i]; p[o + 2] = hava.z[i];
        p[o + 3] = x; p[o + 4] = hava.y[i] + 0.85; p[o + 5] = hava.z[i] - 0.45;
      }
      hava.cizgi.geometry.attributes.position.needsUpdate = true;
    }
    yagmurSesi(y);
    // şimşek
    if (y > 0.6) {
      G.simsek -= dt;
      if (G.simsek <= 0) { G.simsek = 7 + Math.random() * 8; if (post) post.flash = 0.7; flas('#e8f0ff'); setTimeout(SES.simsek, 350 + Math.random() * 500); }
    }
    // kahve buharı
    if (calisiyor && !G.ol && G.geri <= 0) {
      G.buhar -= dt;
      if (G.buhar <= 0) {
        G.buhar = 0.11;
        var sp = fx.buhar.find(function (q) { return !q.visible; });
        if (sp) { B.fincan.getWorldPosition(_vp); sp.visible = true; sp.position.set(_vp.x + (Math.random() - 0.5) * 0.05, _vp.y + 0.28, _vp.z); sp.userData.omur = 0.9; sp.scale.setScalar(0.12); }
      }
    }
    fx.buhar.forEach(function (q) {
      if (!q.visible) return;
      q.userData.omur -= dt; if (q.userData.omur <= 0) { q.visible = false; return; }
      q.position.y += dt * 0.7; q.position.z += (G.hiz || 0) * dt * 0.9; q.position.x += (Math.random() - 0.5) * dt * 0.3;
      var k = 1 - q.userData.omur / 0.9; q.scale.setScalar(0.12 + k * 0.5); q.material.opacity = 0.34 * (1 - k);
    });
  }

  /* =====================================================================
     SON İŞLEME: bloom + hız bulanıklığı + renk ayarı + vinyet (başarısız olursa kapanır, oyun normal çizilir)
     ===================================================================== */
  var post = null;
  var PS_VERT = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';
  var PS_PARLAK = 'uniform sampler2D tD; uniform vec2 texel; uniform float esik; varying vec2 vUv; void main(){ vec3 c = texture2D(tD, vUv + texel * vec2(-1.0,-1.0)).rgb + texture2D(tD, vUv + texel * vec2(1.0,-1.0)).rgb + texture2D(tD, vUv + texel * vec2(-1.0,1.0)).rgb + texture2D(tD, vUv + texel * vec2(1.0,1.0)).rgb; c *= 0.25; float l = max(c.r, max(c.g, c.b)); float k = smoothstep(esik, esik + 0.55, l); gl_FragColor = vec4(c * k, 1.0); }';
  var PS_BULANIK = 'uniform sampler2D tD; uniform vec2 yon; varying vec2 vUv; void main(){ vec3 c = texture2D(tD, vUv).rgb * 0.2270270; c += (texture2D(tD, vUv + yon * 1.3846154).rgb + texture2D(tD, vUv - yon * 1.3846154).rgb) * 0.3162162; c += (texture2D(tD, vUv + yon * 3.2307692).rgb + texture2D(tD, vUv - yon * 3.2307692).rgb) * 0.0702703; gl_FragColor = vec4(c, 1.0); }';
  var PS_BIRLESTIR = [
    'uniform sampler2D tS; uniform sampler2D tB1; uniform sampler2D tB2;',
    'uniform float bloom; uniform float vig; uniform float aber; uniform float hizR; uniform float soguk; uniform float flash; uniform float gece; uniform vec2 merkez;',
    'varying vec2 vUv;',
    'void main(){',
    '  vec2 d = vUv - merkez; float r = length(d);',
    '  vec3 c = vec3(0.0);',
    '  float a = hizR * 0.05 * smoothstep(0.08, 0.6, r);',
    '  for (int i = 0; i < 6; i++) { float t = float(i) / 5.0; c += texture2D(tS, vUv - d * a * t).rgb; }',
    '  c /= 6.0;',
    '  float ab = aber * 0.012 * r + soguk * 0.0025 * r;',
    '  c.r = mix(c.r, texture2D(tS, vUv - d * ab * 3.0).r, min(1.0, (aber + soguk) * 2.0));',
    '  c.b = mix(c.b, texture2D(tS, vUv + d * ab * 3.0).b, min(1.0, (aber + soguk) * 2.0));',
    '  c += bloom * (texture2D(tB1, vUv).rgb * 0.7 + texture2D(tB2, vUv).rgb * 0.95);',
    '  c += vec3(flash);',
    '  vec3 ust = max(c - 0.82, 0.0); c = min(c, vec3(0.82)) + 0.18 * (1.0 - exp(-ust / 0.18));',
    '  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));',
    '  c = mix(vec3(l), c, 1.10 - soguk * 0.4);',
    '  c = mix(c, c * vec3(0.78, 0.95, 1.22), soguk);',
    '  c = (c - 0.5) * 1.05 + 0.5;',
    '  float v = smoothstep(1.0, 0.28, r * 1.25);',
    '  c *= mix(1.0 - vig, 1.0, v);',
    '  gl_FragColor = vec4(max(c, 0.0), 1.0);',
    '  gl_FragColor = linearToOutputTexel(gl_FragColor);',
    '}'
  ].join('\n');

  function postKur() {
    try {
      if (!renderer.capabilities.isWebGL2) return;
      var tip = (renderer.extensions.has('EXT_color_buffer_float') || renderer.extensions.has('EXT_color_buffer_half_float')) ? T.HalfFloatType : T.UnsignedByteType;
      function hedef(msaa) {
        var rt = new T.WebGLRenderTarget(8, 8, { type: tip, format: T.RGBAFormat, minFilter: T.LinearFilter, magFilter: T.LinearFilter, depthBuffer: !!msaa, samples: msaa ? 4 : 0 });
        rt.texture.generateMipmaps = false; return rt;
      }
      post = {
        aktif: true, bloom: 0.55, vig: 0.34, aber: 0, flash: 0, esik: 0.88,
        rt: hedef(true), a1: hedef(false), b1: hedef(false), a2: hedef(false), b2: hedef(false),
        sahne: new T.Scene(), kam: new T.OrthographicCamera(-1, 1, 1, -1, 0, 1)
      };
      post.quad = new T.Mesh(new T.PlaneGeometry(2, 2), null); post.quad.frustumCulled = false; post.sahne.add(post.quad);
      function sm(f, u) { return new T.ShaderMaterial({ vertexShader: PS_VERT, fragmentShader: f, uniforms: u, depthTest: false, depthWrite: false }); }
      post.mParlak = sm(PS_PARLAK, { tD: { value: null }, texel: { value: new T.Vector2() }, esik: { value: post.esik } });
      post.mBulanik = sm(PS_BULANIK, { tD: { value: null }, yon: { value: new T.Vector2() } });
      post.mBirlestir = sm(PS_BIRLESTIR, {
        tS: { value: null }, tB1: { value: null }, tB2: { value: null }, bloom: { value: post.bloom }, vig: { value: post.vig }, aber: { value: 0 },
        hizR: { value: 0 }, soguk: { value: 0 }, flash: { value: 0 }, gece: { value: 0 }, merkez: { value: new T.Vector2(0.5, 0.46) }
      });
      kok.classList.add('post-acik');
    } catch (e) { post = null; if (window.console) console.warn('Son işleme kapalı:', e); }
  }
  function postBoyutla() {
    if (!post) return;
    var v = new T.Vector2(); renderer.getDrawingBufferSize(v);
    var w = Math.max(2, v.x | 0), h = Math.max(2, v.y | 0);
    post.rt.setSize(w, h);
    post.a1.setSize(Math.max(2, w >> 2), Math.max(2, h >> 2)); post.b1.setSize(post.a1.width, post.a1.height);
    post.a2.setSize(Math.max(2, w >> 3), Math.max(2, h >> 3)); post.b2.setSize(post.a2.width, post.a2.height);
  }
  function postGec(mat, hedef) { post.quad.material = mat; renderer.setRenderTarget(hedef); renderer.render(post.sahne, post.kam); }
  function postCiz(dt) {
    var sog = G ? Math.max(0, Math.min(1, (1 - G.zm) / 0.42)) : 0;
    var hizR = (G && !G.ol && durum === 'oyun' && G.geri <= 0) ? Math.max(0, (G.hiz - 10) / 8) * 0.9 + (G.guc > 0 ? 0.35 : 0) + G.hizPuls * 0.5 : 0;
    post.flash = Math.max(0, post.flash - dt * 1.8); post.aber = Math.max(0, post.aber - dt * 1.6);
    renderer.setRenderTarget(post.rt); renderer.render(scene, kamera);
    var m = post.mParlak; m.uniforms.tD.value = post.rt.texture; m.uniforms.texel.value.set(1 / post.rt.width, 1 / post.rt.height); m.uniforms.esik.value = post.esik - (dunya.gece || 0) * 0.12;
    postGec(m, post.a1);
    var b = post.mBulanik;
    b.uniforms.tD.value = post.a1.texture; b.uniforms.yon.value.set(1 / post.a1.width, 0); postGec(b, post.b1);
    b.uniforms.tD.value = post.b1.texture; b.uniforms.yon.value.set(0, 1 / post.a1.height); postGec(b, post.a1);
    b.uniforms.tD.value = post.a1.texture; b.uniforms.yon.value.set(2 / post.a2.width, 0); postGec(b, post.b2);
    b.uniforms.tD.value = post.b2.texture; b.uniforms.yon.value.set(0, 2 / post.a2.height); postGec(b, post.a2);
    b.uniforms.tD.value = post.a2.texture; b.uniforms.yon.value.set(1 / post.a2.width, 0); postGec(b, post.b2);
    b.uniforms.tD.value = post.b2.texture; b.uniforms.yon.value.set(0, 1 / post.a2.height); postGec(b, post.a2);
    var u = post.mBirlestir.uniforms;
    u.tS.value = post.rt.texture; u.tB1.value = post.a1.texture; u.tB2.value = post.a2.texture;
    u.bloom.value = post.bloom + (dunya.gece || 0) * 0.25 + (G ? G.yagmur * 0.12 : 0); u.vig.value = post.vig; u.aber.value = post.aber; u.hizR.value = hizR; u.soguk.value = sog;
    u.flash.value = post.flash * 0.35; u.gece.value = dunya.gece || 0;
    postGec(post.mBirlestir, null);
  }

  /* =====================================================================
     OYUN MANTIĞI
     ===================================================================== */
  function sifirla() {
    if (G) { G.engeller.forEach(function (o) { scene.remove(o.g); }); G.cekirdekler.forEach(function (o) { scene.remove(o.g); }); }
    G = {
      hiz: 0, mesafe: 0, sure: 0, skor: 0, cekirdek: 0, kombo: 0, komboZaman: 0, seviye: 1,
      serit: 0, x: 0, y: 0, vy: 0, kayma: 0, yerde: true, ziplamaSayisi: 0, metre: 0, faz: 0, zm: 1, temiz: 0, hizOr: 0,
      engeller: [], cekirdekler: [], spawnZ: -50, hedefHiz: 9.5, guc: 0, gucToplam: 7, soguk: 0, mikn: 0, yagmur: 0, yagmurHedef: 0, islak: 0, simsek: 8, buhar: 0,
      ol: false, olZaman: 0, sarsinti: 0, geri: 0, geriSon: 99, sonSatir: '', adimZ: 0, tozZ: 0, zamanOlcek: 1, hizPuls: 0
    };
    parcaciklar.forEach(function (p) { p.m.visible = false; });
    B.grup.position.set(0, 0, 0); B.grup.rotation.set(0, Math.PI, 0); B.kalkan.visible = false;
    B.aura.material.opacity = 0;
    hGucKap.hidden = true; kok.classList.remove('soguk'); if (hSog) { hSog.kap.hidden = true; hMik.kap.hidden = true; }
    hSevBar.style.width = '0%'; hSev.textContent = 'Seviye 1'; hMesafe.textContent = '0 m'; hSkor.textContent = '0'; hCekirdek.textContent = '0';
  }

  function nesneAl(tip) { var g = PROTO[tip].clone(true); g.visible = true; scene.add(g); return g; }

  function satirUret() {
    var sev = G.seviye, zorluk = Math.min(1, (sev - 1) / 6);
    var aralikSn = Math.max(0.8, 1.55 - (sev - 1) * 0.07) + Math.random() * 0.5;
    var aralik = Math.max(G.hedefHiz, 10) * aralikSn;
    if (G.sonSatir === 'pankart') aralik *= 1.25;
    G.spawnZ -= aralik;
    var wz = G.spawnZ, r = Math.random(), satir;
    var alcak = ['fincan', 'burger', 'kruvasan', 'donut'], uzun = ['bardak', 'makine'];
    function ekle(tipAd, s) {
      var g = nesneAl(tipAd), d = PROTO[tipAd].userData;
      G.engeller.push({ g: g, wz: wz, lane: s, tip: tipAd, y0: d.y0, y1: d.y1, tum: !!d.tum, kirik: false });
      g.position.set(s * SERIT, 0, 0); g.rotation.y = (Math.random() - 0.5) * 0.4;
    }
    if (G.mesafe < 45) satir = 'bos';
    else if (r < 0.32) satir = 'alcak1';
    else if (r < 0.5) satir = 'alcak2';
    else if (r < 0.68 + zorluk * 0.05) satir = 'uzun1';
    else if (r < 0.8 + zorluk * 0.06) satir = 'uzun2';
    else if (r < 0.9) satir = 'pankart';
    else satir = 'alcakUzun';
    if (sev < 2 && (satir === 'uzun2' || satir === 'pankart' || satir === 'alcakUzun')) satir = 'alcak1';
    G.sonSatir = satir;
    var seritler = [-1, 0, 1].sort(function () { return Math.random() - 0.5; });
    var A = alcak[Math.floor(Math.random() * 4)], Bk = uzun[Math.floor(Math.random() * 2)];
    var bosSerit = seritler[2];
    if (satir === 'alcak1') ekle(A, seritler[0]);
    else if (satir === 'alcak2') { ekle(A, seritler[0]); ekle(alcak[Math.floor(Math.random() * 4)], seritler[1]); if (zorluk > 0.4 && Math.random() < 0.4) ekle(A, seritler[2]); }
    else if (satir === 'uzun1') ekle(Bk, seritler[0]);
    else if (satir === 'uzun2') { ekle(Bk, seritler[0]); ekle(uzun[Math.floor(Math.random() * 2)], seritler[1]); }
    else if (satir === 'alcakUzun') { ekle(Bk, seritler[0]); ekle(A, seritler[1]); }
    else if (satir === 'pankart') ekle('pankart', 0);

    if (Math.random() < 0.65 || satir === 'bos') {
      var cs = (satir === 'pankart' || satir === 'bos') ? seritler[Math.floor(Math.random() * 3)] : bosSerit;
      if (satir === 'alcak1') cs = Math.random() < 0.5 ? seritler[0] : bosSerit;
      var yay = (satir === 'alcak1' && cs === seritler[0]);
      var n = yay ? 7 : 6, orta = wz + aralik * 0.5;
      for (var i = 0; i < n; i++) {
        var cz = yay ? wz + (i - 3) * 1.4 : orta + (i - 2.5) * 1.8;
        var cy = yay ? 1.0 + Math.sin(i / (n - 1) * Math.PI) * 1.05 : 0.9;
        var cg = nesneAl('cekirdek'); cg.position.set(cs * SERIT, cy, 0);
        G.cekirdekler.push({ g: cg, wz: cz, lane: cs, y: cy, alindi: false });
      }
    }
    if (G.mesafe > 150 && Math.random() < 0.14) {
      var turler = [];
      if (!G.guc) turler.push('guc');
      if (!G.soguk) turler.push('soguk');
      if (!G.mikn) turler.push('mikn');
      var vardiMi = G.cekirdekler.some(function (q) { return q.tur && !q.alindi; });
      if (turler.length && !vardiMi) {
        var tur = turler[Math.floor(Math.random() * turler.length)], gs = bosSerit, gg = nesneAl(tur);
        gg.position.set(gs * SERIT, 1.1, 0);
        G.cekirdekler.push({ g: gg, wz: wz + aralik * 0.5, lane: gs, y: 1.1, alindi: false, tur: tur });
      }
    }
  }

  function mesaj(metin, ms, buyuk) {
    hMesaj.textContent = metin; hMesaj.classList.toggle('buyuk', !!buyuk); hMesaj.classList.add('goster');
    clearTimeout(mesaj._t); mesaj._t = setTimeout(function () { hMesaj.classList.remove('goster'); }, ms || 1400);
  }
  function flas(renk) {
    if (!elFlas) return;
    elFlas.style.background = renk || '#fff'; elFlas.classList.remove('yan'); void elFlas.offsetWidth; elFlas.classList.add('yan');
    if (post) post.flash = Math.max(post.flash, 0.5);
  }

  function seriteGit(yon) {
    if (G.geri > 0 || G.ol) return;
    var n = G.serit + yon;
    if (n < -1 || n > 1) { G.sarsinti = Math.max(G.sarsinti, 0.08); return; }
    G.serit = n; SES.serit();
  }
  function zipla() {
    if (G.geri > 0 || G.ol) return;
    if (G.yerde) { G.vy = ZIPLAMA_V; G.yerde = false; G.ziplamaSayisi = 1; G.kayma = 0; SES.ziplama(); for (var i = 0; i < 4; i++) tozAt(G.x, 0.3); }
    else if (G.ziplamaSayisi < 2 && G.vy < 4) { G.vy = ZIPLAMA_V * 0.82; G.ziplamaSayisi = 2; SES.ziplama(); parcacikPatlat(G.x, G.y + 0.4, 0, [0xffffff, KREMA], 10, 3); }
  }
  function kay() {
    if (G.geri > 0 || G.ol) return;
    if (!G.yerde) G.vy = -20;
    G.kayma = 0.75; SES.kayma();
  }

  function titre(p) { try { if (navigator.vibrate) navigator.vibrate(p); } catch (e) {} }

  /* güç çubukları (Espresso / Cold Brew / Mıknatıs) */
  var hSog = null, hMik = null;
  function cubukYap(ad, renk, grad) {
    var k = hGucKap.cloneNode(true); k.hidden = true; k.removeAttribute('id');
    k.querySelector('span').textContent = ad; k.style.color = renk;
    var b = k.querySelector('.kh-guc-iz > div'); b.removeAttribute('id'); b.style.background = grad;
    hGucKap.parentNode.insertBefore(k, hGucKap.nextSibling);
    return { kap: k, bar: b };
  }
  function gucCubuklari() {
    if (!hSog) { hSog = cubukYap('Cold Brew', '#9fd8ff', 'linear-gradient(90deg,#4aa8ff,#d6f0ff)'); hMik = cubukYap('Mıknatıs', '#ffb09c', 'linear-gradient(90deg,#e0554b,#ffd0c4)'); }
    [[G.guc, G.gucToplam, hGucKap, hGucBar], [G.soguk, 7, hSog.kap, hSog.bar], [G.mikn, 9, hMik.kap, hMik.bar]].forEach(function (x) {
      var a = x[0] > 0; if (x[2].hidden === a) x[2].hidden = !a;
      if (a) x[3].style.width = Math.max(0, x[0] / x[1] * 100).toFixed(1) + '%';
    });
  }
  function gucAl(tur) {
    if (tur === 'guc') {
      G.guc = G.gucToplam; B.kalkan.visible = true; SES.guc(); flas('#fff0b8'); titre([20, 40, 20]);
      mesaj('ESPRESSO! Çift puan, engelleri kır', 1800);
      parcacikPatlat(G.x, 1, 0, [0xffd36a, 0xffffff], 22, 7);
    } else if (tur === 'soguk') {
      G.soguk = 7; kok.classList.add('soguk'); SES.soguk(); flas('#a8dcff'); titre([30, 50, 30]);
      mesaj('COLD BREW! Zaman yavaşladı', 1800);
      parcacikPatlat(G.x, 1.2, 0, [0xa8dcff, 0xffffff, 0x6fc3ff], 26, 6);
    } else if (tur === 'mikn') {
      G.mikn = 9; SES.mikn(); flas('#ffb4a4'); titre([15, 30, 15]);
      mesaj('MIKNATIS! Çekirdekler sana akıyor', 1800);
      parcacikPatlat(G.x, 1.2, 0, [0xe0554b, 0xffffff, 0xffd36a], 22, 6);
    }
  }

  function seviyeAtla() {
    G.seviye++; G.hizPuls = 1;
    SES.seviye(); flas('#ffe9a8'); titre([30, 40, 30, 40, 70]);
    mesaj('SEVİYE ' + G.seviye + ' · HIZ ARTTI!', 2000, true);
    parcacikPatlat(G.x, 2.2, -1, [KREMA, MAVI, 0xffffff, 0xe0554b], 36, 9);
  }

  function bitir() {
    if (post) post.aber = 1;
    G.ol = true; G.olZaman = 0; G.sarsinti = 0.8; G.zamanOlcek = 0.28; durum = 'bitis';
    SES.carpma(); flas('#ff5a4d'); titre(140); kok.classList.remove('soguk');
    parcacikPatlat(G.x, G.y + 1, 0, [MAVI, 0xffffff, KREMA, 0x5b3317, 0xe0554b], 46, 9);
    hGucKap.hidden = true;
    var bitisSkor = Math.floor(G.skor), yeni = bitisSkor > ENIYI;
    var sev = G.seviye, mt = Math.floor(G.metre), cek = G.cekirdek, sure = Math.floor(G.sure);
    setTimeout(function () {
      $('kb-skor').textContent = bitisSkor;
      $('kb-detay').textContent = mt + ' m · ' + cek + ' çekirdek · Seviye ' + sev;
      $('kb-rekor').hidden = !yeni;
      if (yeni) { ENIYI = bitisSkor; SES.guc(); }
      $('kb-sira').textContent = bitisSkor > 0 && sure >= 3 ? 'Skor kaydediliyor…' : '';
      elBitis.hidden = false;
      skorGonder(bitisSkor, sure);
    }, 1100);
  }

  var gonderildi = false;
  function skorGonder(skor, sure) {
    if (skor <= 0 || sure < 3) return;
    var fd = new FormData(); fd.append('skor', skor); fd.append('sure_sn', sure); fd.append('csrfmiddlewaretoken', CSRF);
    fetch(URL_SKOR, { method: 'POST', body: fd, credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var el = $('kb-sira');
        if (j && j.ok) { gonderildi = true; el.textContent = j.hafta_sira ? 'Bu hafta ' + j.hafta_sira + '. sıradasın' : 'Skorun kaydedildi'; }
        else el.textContent = 'Skor kaydedilemedi' + ((j && j.mesaj) ? ' (' + j.mesaj + ')' : '');
      })
      .catch(function () { $('kb-sira').textContent = 'Bağlantı hatası: skor kaydedilemedi'; });
  }

  function dunyayiKaydir(d) {
    dunya.yolDoku.offset.y -= d / (420 / 18);
    dunya.binalar.forEach(function (b) { b.z += d; if (b.z > 30) b.z -= dunya.binaBoy; b.g.position.z = b.z; });
    dunya.lambalar.forEach(function (l) { l.z += d; if (l.z > 20) l.z -= dunya.lambaBoy; l.g.position.z = l.z; });
    dunya.agaclar.forEach(function (a) { a.z += d; if (a.z > 20) a.z -= dunya.agacBoy; a.g.position.z = a.z; });
    dunya.masalar.forEach(function (a) { a.z += d; if (a.z > 20) a.z -= dunya.masaBoy; a.g.position.z = a.z; });
    dunya.props.forEach(function (a) { a.z += d; if (a.z > 20) a.z -= dunya.propBoy; a.g.position.z = a.z; });
    dunya.kayan.forEach(function (a) { a.z += d; if (a.z > 20) a.z -= a.boy; a.g.position.z = a.z; });
  }

  function guncelle(dt) {
    var kl = B.grup;
    if (G.ol) {
      G.olZaman += dt; G.hiz *= Math.pow(0.02, dt);
      kl.rotation.x += dt * 5; kl.position.y += (G.olZaman < 0.3 ? 4.2 : -6.5) * dt; if (kl.position.y < 0) kl.position.y = 0;
      kl.position.z += dt * 2;
      return;
    }
    // geri sayım
    if (G.geri > 0) {
      G.geri -= dt;
      var sn = Math.ceil(G.geri);
      if (sn !== G.geriSon && sn > 0) { G.geriSon = sn; hGeri.textContent = sn; hGeri.classList.remove('vur'); void hGeri.offsetWidth; hGeri.classList.add('vur'); SES.geri(false); }
      kl.rotation.y += (0 - kl.rotation.y) * Math.min(1, dt * 5);
      poz('bekle', 0, performance.now() / 1000, dt);
      if (G.geri <= 0) { hGeri.textContent = 'KOŞ!'; hGeri.classList.remove('vur'); void hGeri.offsetWidth; hGeri.classList.add('vur'); SES.geri(true); setTimeout(function () { hGeri.textContent = ''; }, 700); }
      return;
    }
    kl.rotation.y += (0 - kl.rotation.y) * Math.min(1, dt * 6);
    // Zaman ölçeği: Cold Brew içilince dünya yavaşlar ("dördüncü boyut" = zaman)
    var gercek = dt;
    G.zm += ((G.soguk > 0 ? 0.58 : 1) - G.zm) * Math.min(1, dt * 4);
    dt *= G.zm;
    G.sure += dt;
    // hız: her 1000 m'de bir kademe
    if (Math.floor(G.metre / SEVIYE_M) + 1 > G.seviye) seviyeAtla();
    G.hedefHiz = hizSeviyeye(G.seviye) + (G.guc > 0 ? 3 : 0);
    G.hiz += (G.hedefHiz - G.hiz) * Math.min(1, dt * 1.6);
    G.hizPuls = Math.max(0, G.hizPuls - dt * 1.2);
    G.mesafe += G.hiz * dt;
    G.metre += G.hiz * dt * METRE_KAT;
    G.skor += G.hiz * dt * METRE_KAT * (G.guc > 0 ? 2 : 1);
    if (G.guc > 0) { G.guc -= gercek; if (G.guc <= 0) { B.kalkan.visible = false; B.aura.material.opacity = 0; } }
    if (G.soguk > 0) { G.soguk -= gercek; if (G.soguk <= 0) { kok.classList.remove('soguk'); } }
    if (G.mikn > 0) { G.mikn -= gercek; }
    gucCubuklari();
    if (G.komboZaman > 0) { G.komboZaman -= dt; if (G.komboZaman <= 0) G.kombo = 0; }

    // oyuncu fiziği
    G.x += (G.serit * SERIT - G.x) * Math.min(1, dt * 15);
    if (!G.yerde) {
      G.vy -= YERCEKIMI * dt; G.y += G.vy * dt;
      if (G.y <= 0) { G.y = 0; G.vy = 0; G.yerde = true; G.ziplamaSayisi = 0; for (var i = 0; i < 5; i++) tozAt(G.x, 0.3); SES.adim(); }
    }
    if (G.kayma > 0) G.kayma -= dt;
    var kayiyor = G.kayma > 0 && G.yerde;
    kl.position.set(G.x, G.y, 0);
    kl.rotation.z = -(G.serit * SERIT - G.x) * 0.08;
    var mod = kayiyor ? 'kayma' : (G.yerde ? 'kos' : 'ziplama');
    // Koşu fazı hıza bağlı: adım sıklığı = hız / adım boyu (ayaklar yolla aynı tempoda akar)
    var hizOr = Math.max(0, Math.min(1, (G.hiz - 9.5) / 7));
    var kad = Math.max(2.6, Math.min(4.6, G.hiz / ADIM_BOY));
    G.faz += dt * kad * 6.2832;
    G.hizOr = hizOr;
    poz(mod, G.faz, G.sure, gercek);
    // ayak sesi + toz
    var adimIdx = Math.floor(G.faz / Math.PI);
    if (G.yerde && !kayiyor && adimIdx !== G.adimZ) { G.adimZ = adimIdx; if (adimIdx % 2 === 0) SES.adim(); tozAt(G.x + (adimIdx % 2 ? 0.2 : -0.2), 0.4); }
    if (kayiyor) { G.tozZ -= dt; if (G.tozZ <= 0) { G.tozZ = 0.05; tozAt(G.x, 0.1); } }
    if (B.kalkan.visible) { var s = 1 / B.olc + Math.sin(G.sure * 8) * 0.05; B.kalkan.scale.setScalar(s); B.aura.material.opacity = 0.55 + Math.sin(G.sure * 8) * 0.15; }
    B.golge.position.x = G.x; var gs = Math.max(0.4, 1 - G.y * 0.2); B.golge.scale.setScalar(gs * (kayiyor ? 1.2 : 1)); B.golge.material.opacity = 0.3 * gs;

    while (G.spawnZ > -(G.mesafe + CIZIM_UZAK)) satirUret();

    // engeller
    var px0 = G.x - 0.4, px1 = G.x + 0.4, pyAlt = G.y, pyUst = G.y + (kayiyor ? 0.7 : 1.7);
    for (var e = G.engeller.length - 1; e >= 0; e--) {
      var o = G.engeller[e], z = o.wz + G.mesafe;
      o.g.position.z = z;
      if (z > 14) { scene.remove(o.g); G.engeller.splice(e, 1); continue; }
      if (o.kirik) { o.g.position.y += dt * 8; o.g.rotation.x += dt * 6; o.g.position.x += dt * 4; continue; }
      if (!o.gecti && z > 1.25) {                  // temiz geçiş bonusu
        o.gecti = true;
        if (o.tum || Math.abs(o.lane * SERIT - G.x) < 1.4) { G.skor += 10; G.temiz++; if (G.temiz % 10 === 0) { mesaj('Temiz koşu x' + G.temiz, 1000); SES.serit(); } }
      }
      if (z > -1.05 && z < 1.05) {
        var cx0, cx1;
        if (o.tum) { cx0 = -999; cx1 = 999; } else { cx0 = o.lane * SERIT - 1.0; cx1 = o.lane * SERIT + 1.0; }
        if (px1 > cx0 && px0 < cx1 && pyUst > o.y0 && pyAlt < o.y1) {
          if (G.guc > 0 || (DEBUG && window.__kosuGod)) { o.kirik = true; SES.kirma(); titre(12); G.sarsinti = 0.25; G.skor += 25; parcacikPatlat(o.g.position.x, 1, 0, [0xffffff, KREMA, 0x5b3317], 18, 8); }
          else { bitir(); return; }
        }
      }
    }
    // çekirdekler + güçlendiriciler
    for (var j = G.cekirdekler.length - 1; j >= 0; j--) {
      var c = G.cekirdekler[j], cz = c.wz + G.mesafe;
      if (G.mikn > 0 && !c.tur && cz > -30 && cz < 4) {       // çekirdek mıknatısı
        var cek = Math.min(1, dt * 6);
        c.wz -= cz * Math.min(1, dt * 3.2); cz = c.wz + G.mesafe;
        c.g.position.x += (G.x - c.g.position.x) * cek; c.y += (G.y + 0.9 - c.y) * cek; c.g.position.y = c.y;
      }
      c.g.position.z = cz; c.g.rotation.y += dt * (c.tur ? 3 : 5);
      if (c.tur) c.g.position.y = 1.1 + Math.sin(G.sure * 4) * 0.12;
      if (cz > 12) { scene.remove(c.g); G.cekirdekler.splice(j, 1); continue; }
      if (!c.alindi && cz > -1.2 && cz < 1.2 && Math.abs(c.g.position.x - G.x) < 1.15 && Math.abs(c.y - (G.y + 0.9)) < 1.25) {
        c.alindi = true; scene.remove(c.g); G.cekirdekler.splice(j, 1);
        if (c.tur) { gucAl(c.tur); }
        else {
          G.kombo++; G.komboZaman = 1.2; G.cekirdek++; G.skor += 5 * (G.guc > 0 ? 2 : 1); SES.cekirdek(G.kombo);
          if (G.kombo % 10 === 0) { G.skor += G.kombo; mesaj('x' + G.kombo + ' KOMBO!  +' + G.kombo, 1100); titre(10); }
          parcacikPatlat(c.g.position.x, c.y, 0, [KREMA, 0xffffff], 4, 3);
        }
      }
    }
    dunyayiKaydir(G.hiz * dt);
    gokGuncelle(G.metre, dt);

    // HUD
    hSkor.textContent = Math.floor(G.skor); hCekirdek.textContent = G.cekirdek;
    hMesafe.textContent = Math.floor(G.metre) + ' m'; hSev.textContent = 'Seviye ' + G.seviye;
    hSevBar.style.width = ((G.metre % SEVIYE_M) / SEVIYE_M * 100).toFixed(1) + '%';
  }

  function kameraGuncelle(dt) {
    var dikey = innerWidth / innerHeight < 0.9;
    var hedefFov = (dikey ? 74 : 60) + (G && G.guc > 0 ? 8 : 0) + (G ? Math.min(G.hiz - 14, 30) * 0.2 : 0) + (G ? G.hizPuls * 10 : 0);
    kamera.fov += (hedefFov - kamera.fov) * Math.min(1, dt * 3); kamera.updateProjectionMatrix();
    var x = G ? G.x * 0.55 : 0, y = dikey ? 5.4 : 4.2, z = dikey ? 9.4 : 7.4;
    var bakX = G ? x * 0.8 : 0, bakY = 1.6, bakZ = -12;
    if (durum === 'menu') { x = 0; y = 2.4; z = 6.2; bakX = 0; bakY = 1.4; bakZ = 0; }
    else if (durum === 'dolap') {
      bakZ = 0; bakY = dikey ? 0.55 : 1.15; x = dikey ? 0 : 1.05; bakX = x; y = dikey ? 1.55 : 1.5; z = dikey ? 4.6 : 3.7;
    }
    var sars = 0;
    if (G && G.sarsinti > 0) { G.sarsinti -= dt; sars = G.sarsinti; }
    var hy = kamera.position;
    hy.x += (x + (Math.random() - 0.5) * sars * 0.6 - hy.x) * Math.min(1, dt * ((durum === 'menu' || durum === 'dolap') ? 3 : 12));
    hy.y += (y + (G ? G.y * 0.25 : 0) + (Math.random() - 0.5) * sars * 0.6 - hy.y) * Math.min(1, dt * 6);
    hy.z += (z - hy.z) * Math.min(1, dt * 4);
    kamera.lookAt(bakX, bakY, bakZ);
    if (G) kamera.rotation.z = -(G.serit * SERIT - G.x) * 0.012;
  }

  /* ---------- döngü + uyarlanabilir kalite ---------- */
  var son = 0;
  function kaliteKontrol(dt) {
    if (DEBUG || durum !== 'oyun') return;
    kalite.n++; kalite.top += dt;
    if (kalite.n >= 80) {
      var ort = kalite.top / kalite.n; kalite.n = 0; kalite.top = 0;
      if (ort > 0.028) {
        if (kalite.pr > 0.8) { kalite.pr = Math.max(0.75, kalite.pr - 0.25); boyutla(); }
        else if (post && post.aktif) { post.aktif = false; kok.classList.remove('post-acik'); }
        else if (gunes.castShadow) { gunes.castShadow = false; scene.traverse(function (o) { if (o.material && o.material.needsUpdate !== undefined) o.material.needsUpdate = true; }); }
      }
    }
  }

  function dongu(t) {
    requestAnimationFrame(dongu);
    var gdt = Math.min((t - son) / 1000, 0.05); son = t;
    var dt = gdt;
    if (G && G.ol) { G.zamanOlcek = Math.min(1, G.zamanOlcek + gdt * 0.9); dt = gdt * G.zamanOlcek; }
    if (durum === 'oyun' || durum === 'bitis') guncelle(dt);
    else if (durum === 'menu' || durum === 'dolap') {
      if (!G) sifirla();
      G.mesafe += 5 * dt; G.metre += 7.5 * dt; dunyayiKaydir(5 * dt); gokGuncelle(G.metre, dt);
      var hedefAci = durum === 'dolap' ? Math.PI + dolapDon : Math.PI + Math.sin(t / 1600) * 0.25;
      B.grup.rotation.y += (hedefAci - B.grup.rotation.y) * Math.min(1, dt * 6);
      poz('selam', 0, t / 1000, dt); B.kalca.position.y = 0.92 + Math.sin(t / 400) * 0.01;
      B.golge.position.x = 0;
    }
    parcacikGuncelle(dt); fxGuncelle(dt);
    kameraGuncelle(gdt);
    havaGuncelle(dt, durum === 'oyun' || durum === 'bitis' || durum === 'dur');
    if (post && post.aktif) {
      try { postCiz(gdt); }
      catch (e) { post.aktif = false; kok.classList.remove('post-acik'); renderer.setRenderTarget(null); if (window.console) console.warn('Son işleme kapatıldı:', e); renderer.render(scene, kamera); }
    } else { renderer.setRenderTarget(null); renderer.render(scene, kamera); }
    if (durum === 'oyun') kaliteKontrol(gdt);
  }

  function boyutla() {
    if (!renderer) return;
    var w = elSahne.clientWidth || innerWidth, h = elSahne.clientHeight || innerHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2) * kalite.pr);
    renderer.setSize(w, h, false); postBoyutla();
    kamera.aspect = w / h; kamera.updateProjectionMatrix();
  }

  function motorKur() {
    if (motorHazir) return;
    renderer = new T.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.outputEncoding = T.sRGBEncoding;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
    renderer.domElement.className = 'kosu-cv';
    elSahne.appendChild(renderer.domElement);
    renderer.domElement.addEventListener('webglcontextlost', function (e) { e.preventDefault(); duraklat(); });
    scene = new T.Scene(); scene.fog = new T.Fog(0xffe3ad, 45, 178);
    kamera = new T.PerspectiveCamera(60, 1, 0.1, 340);
    kamera.position.set(0, 2.4, 6.2);
    hemi = new T.HemisphereLight(0xdff0ff, 0x8b7a5a, 0.95); scene.add(hemi);
    gunes = new T.DirectionalLight(0xfff0d0, 1.5); gunes.position.set(-8, 18, 4);
    gunes.target.position.set(0, 0, -14); scene.add(gunes.target);
    gunes.castShadow = true; gunes.shadow.mapSize.set(1024, 1024);
    var sc = gunes.shadow.camera; sc.left = -13; sc.right = 13; sc.top = 26; sc.bottom = -26; sc.near = 1; sc.far = 60; gunes.shadow.bias = -0.0004; gunes.shadow.normalBias = 0.03;
    scene.add(gunes);
    dolgu = new T.DirectionalLight(0x9db8ff, 0.35); dolgu.position.set(8, 6, -10); scene.add(dolgu);
    baristaKur(); protoKur(); dunyaKur(); fxKur(); havaKur(); postKur();
    giydir(); dolapKur();
    motorHazir = true; boyutla();
    window.addEventListener('resize', boyutla);
    requestAnimationFrame(function (t) { son = t; dongu(t); });
  }

  /* ---------- akış: aç / başla / duraklat / kapat ---------- */
  function tamEkran() {
    try { var f = kok.requestFullscreen || kok.webkitRequestFullscreen; if (f) { var p = f.call(kok); if (p && p.catch) p.catch(function () {}); } } catch (x) {}
  }
  function tamEkrandanCik() {
    try { if (document.fullscreenElement || document.webkitFullscreenElement) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); } } catch (x) {}
  }
  function ac() {
    kok.hidden = false; document.documentElement.classList.add('kosu-acik'); radyoKur();
    tamEkran(); sesBaslat();
    if (!motorHazir) { try { motorKur(); } catch (e) { kok.hidden = true; document.documentElement.classList.remove('kosu-acik'); alert('Bu cihazda 3B oyun başlatılamadı.'); return; } }
    else boyutla();
    durum = 'menu'; sifirla(); kok.classList.add('menude'); elMenu.hidden = false; elBitis.hidden = true; elDur.hidden = true; elDolap.hidden = true;
    dolapKur(); giydir();
    setTimeout(boyutla, 120);
  }
  function dolapAc() {
    if (durum !== 'menu') return;
    durum = 'dolap'; elMenu.hidden = true; elDolap.hidden = false; dolapDon = 0; dolapKur();
  }
  function dolapKapat() {
    if (durum !== 'dolap') return;
    durum = 'menu'; elDolap.hidden = true; elMenu.hidden = false;
  }
  function menuyeDon() {            // oyun bitince "Kıyafet değiştir"
    durum = 'menu'; sifirla(); kok.classList.add('menude'); elBitis.hidden = true; elDur.hidden = true; elMenu.hidden = false; elDolap.hidden = true;
    dolapAc();
  }
  function kapat() {
    durum = 'menu'; kok.hidden = true; document.documentElement.classList.remove('kosu-acik'); kok.classList.remove('soguk');
    tamEkrandanCik();
    if (gonderildi) location.reload();
  }
  function basla() {
    sesBaslat(); sifirla(); kok.classList.remove('menude'); durum = 'oyun';
    elMenu.hidden = true; elBitis.hidden = true; elDur.hidden = true; elDolap.hidden = true;
    G.geri = 3.0; G.geriSon = 99; hGeri.textContent = '';
    gokGuncelle(0, 0); giydir();
  }
  function duraklat() { if (durum !== 'oyun') return; durum = 'dur'; elDur.hidden = false; }
  function surdur() { if (durum !== 'dur') return; elDur.hidden = true; durum = 'oyun'; son = performance.now(); }

  if (DEBUG) window.__kosu = {
    g: function () { return G; }, ac: ac, basla: basla, post: function () { return post; }, k: function () { return K; }, durum: function () { return durum; },
    eniyi: function (n) { ENIYI = n; dolapKur(); giydir(); }, seri: seriteGit, zipla: zipla, kay: kay, giydir: giydir, dolapAc: dolapAc,
    adim: function (n, dt) { for (var i = 0; i < n; i++) { if (G.ol) return; guncelle(dt); havaGuncelle(dt, true); } }
  };

  /* ---------- girdiler ---------- */
  window.addEventListener('keydown', function (e) {
    if (kok.hidden) return;
    var k = e.code;
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Space'].indexOf(k) >= 0) e.preventDefault();
    if (e.repeat) return;
    if (k === 'KeyR' && durum !== 'bitis') { radyoDegistir(); return; }
    if (durum === 'dolap') { if (k === 'Escape' || k === 'Enter' || k === 'Space') dolapKapat(); return; }
    if (durum === 'menu') { if (k === 'Space' || k === 'Enter') basla(); else if (k === 'KeyG') dolapAc(); return; }
    if (durum === 'bitis') { if (G.ol && G.olZaman > 0.9 && (k === 'Space' || k === 'Enter') && !elBitis.hidden) basla(); return; }
    if (durum === 'dur') { if (k === 'KeyP' || k === 'Escape' || k === 'Space') surdur(); return; }
    if (k === 'ArrowLeft' || k === 'KeyA') seriteGit(-1);
    else if (k === 'ArrowRight' || k === 'KeyD') seriteGit(1);
    else if (k === 'ArrowUp' || k === 'KeyW' || k === 'Space') zipla();
    else if (k === 'ArrowDown' || k === 'KeyS') kay();
    else if (k === 'KeyP') duraklat();
  });

  var dolapSurukle = null;
  elSahne.addEventListener('pointerdown', function (e) { if (durum === 'dolap') dolapSurukle = { x: e.clientX, d: dolapDon }; });
  window.addEventListener('pointermove', function (e) { if (dolapSurukle && durum === 'dolap') dolapDon = dolapSurukle.d + (e.clientX - dolapSurukle.x) * 0.012; });
  window.addEventListener('pointerup', function () { dolapSurukle = null; });
  var dok = null;
  elSahne.addEventListener('pointerdown', function (e) { if (durum !== 'oyun') return; dok = { x: e.clientX, y: e.clientY, t: performance.now(), tamam: false }; });
  elSahne.addEventListener('pointermove', function (e) {
    if (!dok || dok.tamam || durum !== 'oyun') return;
    var dx = e.clientX - dok.x, dy = e.clientY - dok.y, esik = 26;
    if (Math.abs(dx) < esik && Math.abs(dy) < esik) return;
    dok.tamam = true;
    if (Math.abs(dx) > Math.abs(dy)) seriteGit(dx > 0 ? 1 : -1); else if (dy < 0) zipla(); else kay();
  });
  elSahne.addEventListener('pointerup', function () {
    if (dok && !dok.tamam && durum === 'oyun' && performance.now() - dok.t < 260) zipla();
    dok = null;
  });
  elSahne.addEventListener('pointercancel', function () { dok = null; });
  elSahne.addEventListener('touchmove', function (e) { e.preventDefault(); }, { passive: false });

  document.addEventListener('visibilitychange', function () { if (document.hidden) duraklat(); });
  function tamEkranDegisti() {
    if (!kok.hidden && !(document.fullscreenElement || document.webkitFullscreenElement)) duraklat();
    setTimeout(boyutla, 80);
  }
  document.addEventListener('fullscreenchange', tamEkranDegisti); document.addEventListener('webkitfullscreenchange', tamEkranDegisti);

  [].forEach.call(document.querySelectorAll('[data-kosu-ac]'), function (b) { b.addEventListener('click', ac); });
  $('kosu-basla').addEventListener('click', basla);
  $('kosu-dolap-ac').addEventListener('click', dolapAc);
  $('kd-bitti').addEventListener('click', dolapKapat);
  $('kosu-dolap-bitis').addEventListener('click', menuyeDon);
  [].forEach.call(document.querySelectorAll('[data-kosu-radyo]'), function (b) { b.addEventListener('click', radyoDegistir); });
  $('kosu-tekrar').addEventListener('click', basla);
  [].forEach.call(document.querySelectorAll('[data-kosu-kapat]'), function (b) { b.addEventListener('click', kapat); });
  $('kosu-duraklat').addEventListener('click', function () { if (durum === 'oyun') duraklat(); else if (durum === 'dur') surdur(); });
  $('kosu-devam').addEventListener('click', surdur);
  $('kosu-tam').addEventListener('click', function () { if (document.fullscreenElement || document.webkitFullscreenElement) tamEkrandanCik(); else tamEkran(); });
})();
