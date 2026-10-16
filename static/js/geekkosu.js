/* Geek Koşusu 3D — üç şeritli, tam ekran sonsuz koşu oyunu (three.js).
   Kontrol: ← → / A D şerit değiştirir · ↑ / W / Boşluk zıplar · ↓ / S kayar · P duraklatır
   Dokunmatik: sağa/sola/yukarı/aşağı kaydır, dokunmak = zıpla. */
(function () {
  'use strict';
  var kok = document.getElementById('kosu-oyun');
  if (!kok || !window.THREE) return;
  var T = THREE;

  /* ---------- sabitler ---------- */
  var SERIT = 2.4;                       // şerit genişliği
  var CIZIM_UZAK = 150;                  // engellerin göründüğü mesafe
  var YERCEKIMI = 30, ZIPLAMA_V = 11.2;
  var MAVI = 0x2a3bd6, KREMA = 0xf2b544, LACI = 0x0b0f2e;
  var URL_SKOR = kok.getAttribute('data-skor-url');
  var LOGO_URL = kok.getAttribute('data-logo');
  var CSRF = (document.querySelector('input[name=csrfmiddlewaretoken]') || {}).value || '';
  var ENIYI = parseInt(kok.getAttribute('data-en') || '0', 10) || 0;

  /* ---------- DOM ---------- */
  function $(id) { return document.getElementById(id); }
  var elSahne = $('kosu-sahne'), elMenu = $('kosu-menu'), elBitis = $('kosu-bitis'), elDur = $('kosu-dur');
  var hSkor = $('kh-skor'), hCekirdek = $('kh-cekirdek'), hHiz = $('kh-hiz'), hGuc = $('kh-guc'), hGucBar = $('kh-guc-bar'), hMesaj = $('kh-mesaj');
  var sesBtn = $('kosu-ses');

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
    ziplama: function () { bip(300, 0.16, 'square', 0.07, 640); },
    kayma: function () { bip(260, 0.18, 'sawtooth', 0.05, 110); },
    serit: function () { bip(420, 0.06, 'triangle', 0.05, 520); },
    cekirdek: function (kombo) { bip(880 * Math.pow(1.06, Math.min(kombo, 10)), 0.12, 'sine', 0.1, 1500); },
    guc: function () { [523, 659, 784, 1046].forEach(function (f, i) { bip(f, 0.18, 'triangle', 0.1, 0, i * 0.07); }); },
    carpma: function () { gurultu(0.5, 0.35); bip(160, 0.5, 'sawtooth', 0.12, 40); },
    kirma: function () { gurultu(0.25, 0.2); bip(500, 0.12, 'square', 0.06, 200); },
    mesafe: function () { [660, 880].forEach(function (f, i) { bip(f, 0.15, 'sine', 0.09, 0, i * 0.1); }); }
  };
  function sesGuncelle() { if (sesBtn) { sesBtn.setAttribute('aria-pressed', ses.kapali ? 'false' : 'true'); sesBtn.textContent = ses.kapali ? 'Ses kapalı' : 'Ses açık'; } }
  sesGuncelle();
  if (sesBtn) sesBtn.addEventListener('click', function () {
    ses.kapali = !ses.kapali; try { localStorage.setItem('kosu_ses', ses.kapali ? '0' : '1'); } catch (e) {}
    sesBaslat(); sesGuncelle();
  });

  /* ---------- three: sahne ---------- */
  var renderer, scene, kamera, hemi, gunes, motorHazir = false;
  var oyuncu = {}, dunya = {};
  var durum = 'menu';                    // menu | oyun | dur | bitis
  var G = null;                          // oyun durumu
  var logoImg = new Image(), logoYuklendi = false, logoTexler = [];
  var parcaciklar = [];
  var gokRenk = {
    gun: new T.Color(0xffe3a8), aksam: new T.Color(0xe98f6b), gece: new T.Color(0x0b0f2e)
  };

  function logoTexture(zemin, w, h, oran) {
    var cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    var tex = new T.CanvasTexture(cv);
    tex.anisotropy = 4;
    function ciz() {
      var c = cv.getContext('2d'); c.fillStyle = zemin; c.fillRect(0, 0, w, h);
      if (logoYuklendi) {
        var lw = w * (oran || 0.78), lh = lw * logoImg.naturalHeight / logoImg.naturalWidth;
        if (lh > h * 0.86) { lh = h * 0.86; lw = lh * logoImg.naturalWidth / logoImg.naturalHeight; }
        c.drawImage(logoImg, (w - lw) / 2, (h - lh) / 2, lw, lh);
      } else {
        c.fillStyle = '#2a3bd6'; c.font = '800 ' + Math.floor(h * 0.6) + 'px system-ui,sans-serif';
        c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('geek', w / 2, h / 2);
      }
      tex.needsUpdate = true;
    }
    ciz(); logoTexler.push(ciz);
    return tex;
  }
  logoImg.onload = function () { logoYuklendi = true; logoTexler.forEach(function (f) { f(); }); };
  logoImg.src = LOGO_URL;

  function std(renk, ekstra) {
    var o = { color: renk, roughness: 0.55, metalness: 0.05 };
    if (ekstra) for (var k in ekstra) o[k] = ekstra[k];
    return new T.MeshStandardMaterial(o);
  }

  /* ---- karakter: 3B "g" harfi ---- */
  function gHarfiGeometri() {
    var R = 1, r = 0.6, s = new T.Shape(), i, a;
    var bas = 38 * Math.PI / 180, son = Math.PI * 2;           // dış yay: sağ üstten başlayıp saat yönünün tersine
    for (i = 0; i <= 48; i++) { a = bas + (son - bas) * i / 48; (i ? s.lineTo : s.moveTo).call(s, Math.cos(a) * R, Math.sin(a) * R); }
    s.lineTo(R, 0.22); s.lineTo(0.12, 0.22); s.lineTo(0.12, -0.1);
    var ic0 = Math.asin(-0.1 / r);                              // iç yayın alt ucu
    var iBas = Math.PI * 2 + ic0;
    for (i = 0; i <= 44; i++) { a = iBas - (iBas - bas) * i / 44; s.lineTo(Math.cos(a) * r, Math.sin(a) * r); }
    s.closePath();
    var g = new T.ExtrudeGeometry(s, { depth: 0.55, bevelEnabled: true, bevelThickness: 0.1, bevelSize: 0.09, bevelSegments: 4, curveSegments: 18 });
    g.center();
    return g;
  }

  function oyuncuKur() {
    var grup = new T.Group();
    var govde = new T.Mesh(gHarfiGeometri(), std(MAVI, { roughness: 0.28, metalness: 0.15, emissive: 0x0a1070, emissiveIntensity: 0.35 }));
    govde.scale.set(0.82, 0.82, 0.82); govde.position.y = 1.05;
    grup.add(govde);
    // logodaki beyaz parlama
    var parla = new T.Mesh(new T.CircleGeometry(0.12, 20), new T.MeshBasicMaterial({ color: 0xffffff }));
    parla.position.set(-0.3, 1.33, 0.46); parla.scale.set(1.1, 0.8, 1); grup.add(parla);
    var parla2 = parla.clone(); parla2.position.set(-0.05, 1.57, 0.46); parla2.scale.set(0.5, 0.35, 1); grup.add(parla2);
    // ayaklar (spor ayakkabı) ve eller
    var ayakM = std(0xffffff, { roughness: 0.4 }), tabanM = std(KREMA, { roughness: 0.5 });
    function ayak() {
      var a = new T.Group();
      var u = new T.Mesh(new T.SphereGeometry(0.3, 14, 10), ayakM); u.scale.set(0.9, 0.55, 1.35); u.position.y = 0.2; a.add(u);
      var t = new T.Mesh(new T.BoxGeometry(0.5, 0.08, 0.78), tabanM); t.position.y = 0.04; a.add(t);
      return a;
    }
    oyuncu.ayakSol = ayak(); oyuncu.ayakSag = ayak();
    oyuncu.ayakSol.position.set(-0.32, 0, 0); oyuncu.ayakSag.position.set(0.32, 0, 0);
    grup.add(oyuncu.ayakSol, oyuncu.ayakSag);
    var elM = std(0xffffff, { roughness: 0.5 });
    function el() { var m = new T.Mesh(new T.SphereGeometry(0.17, 12, 10), elM); return m; }
    oyuncu.elSol = el(); oyuncu.elSag = el();
    oyuncu.elSol.position.set(-0.95, 1.0, 0); oyuncu.elSag.position.set(0.95, 1.0, 0);
    grup.add(oyuncu.elSol, oyuncu.elSag);
    // gölge
    oyuncu.golge = new T.Mesh(new T.CircleGeometry(0.75, 24), new T.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28, depthWrite: false }));
    oyuncu.golge.rotation.x = -Math.PI / 2; oyuncu.golge.position.y = 0.02;
    // kalkan (espresso gücü)
    oyuncu.kalkan = new T.Mesh(new T.SphereGeometry(1.45, 24, 18), new T.MeshBasicMaterial({ color: 0xffd36a, transparent: true, opacity: 0.22, depthWrite: false }));
    oyuncu.kalkan.position.y = 1.05; oyuncu.kalkan.visible = false; grup.add(oyuncu.kalkan);
    oyuncu.govde = govde; oyuncu.grup = grup;
    scene.add(grup); scene.add(oyuncu.golge);
  }

  /* ---- engel prototipleri (Geek logolu) ---- */
  var PROTO = {};
  function protoKur() {
    var beyaz = std(0xffffff, { roughness: 0.35 }), laci = std(LACI, { roughness: 0.5 }), krem = std(KREMA, { roughness: 0.45 });
    var kahve = std(0x5b3317, { roughness: 0.4 });
    function decal(w, h, zemin, oran) {
      var m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ map: logoTexture(zemin, 512, Math.round(512 * h / w), oran) }));
      return m;
    }

    // Fincan (alçak)
    var f = new T.Group();
    var tabak = new T.Mesh(new T.CylinderGeometry(0.95, 0.75, 0.1, 28), krem); tabak.position.y = 0.05; f.add(tabak);
    var bardak = new T.Mesh(new T.CylinderGeometry(0.72, 0.5, 0.78, 28), beyaz); bardak.position.y = 0.49; f.add(bardak);
    var kah = new T.Mesh(new T.CylinderGeometry(0.64, 0.64, 0.03, 28), kahve); kah.position.y = 0.87; f.add(kah);
    var kulp = new T.Mesh(new T.TorusGeometry(0.22, 0.06, 10, 20), beyaz); kulp.position.set(0.78, 0.5, 0); f.add(kulp);
    var d1 = decal(0.78, 0.4, '#ffffff', 0.9); d1.position.set(0, 0.5, 0.64); d1.rotation.x = -0.08; f.add(d1);
    f.userData = { y0: 0, y1: 0.95, yari: 0.85 }; PROTO.fincan = f;

    // Take-away bardak (uzun)
    var b = new T.Group();
    var gov = new T.Mesh(new T.CylinderGeometry(0.78, 0.55, 2.2, 28), beyaz); gov.position.y = 1.1; b.add(gov);
    var kap = new T.Mesh(new T.CylinderGeometry(0.86, 0.82, 0.22, 28), laci); kap.position.y = 2.3; b.add(kap);
    var kapUst = new T.Mesh(new T.CylinderGeometry(0.62, 0.86, 0.14, 28), laci); kapUst.position.y = 2.48; b.add(kapUst);
    var kol = new T.Mesh(new T.CylinderGeometry(0.71, 0.63, 0.9, 28, 1, true), krem); kol.position.y = 1.0; b.add(kol);
    var d2 = decal(1.1, 0.62, '#ffffff', 0.92); d2.position.set(0, 1.18, 0.77); b.add(d2);
    b.userData = { y0: 0, y1: 2.6, yari: 0.8 }; PROTO.bardak = b;

    // Burger (alçak)
    var g = new T.Group();
    var altEkmek = new T.Mesh(new T.CylinderGeometry(0.85, 0.8, 0.22, 26), std(0xe0a24e)); altEkmek.position.y = 0.11; g.add(altEkmek);
    var kofte = new T.Mesh(new T.CylinderGeometry(0.88, 0.88, 0.2, 26), std(0x6b3418)); kofte.position.y = 0.32; g.add(kofte);
    var peynir = new T.Mesh(new T.BoxGeometry(1.5, 0.05, 1.5), std(0xffc93a)); peynir.position.y = 0.46; peynir.rotation.y = Math.PI / 4; g.add(peynir);
    var marul = new T.Mesh(new T.TorusGeometry(0.82, 0.1, 8, 24), std(0x4fb04f)); marul.rotation.x = Math.PI / 2; marul.position.y = 0.52; marul.scale.z = 0.6; g.add(marul);
    var ustEkmek = new T.Mesh(new T.SphereGeometry(0.88, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), std(0xe0a24e)); ustEkmek.position.y = 0.55; ustEkmek.scale.y = 0.85; g.add(ustEkmek);
    for (var i = 0; i < 9; i++) {
      var susam = new T.Mesh(new T.SphereGeometry(0.05, 6, 4), std(0xfff4d6)); susam.scale.y = 0.5;
      var aa = i * 0.7, rr = 0.2 + (i % 3) * 0.2; susam.position.set(Math.cos(aa) * rr, 1.18 - rr * 0.38, Math.sin(aa) * rr + 0.1); g.add(susam);
    }
    var bayrak = decal(0.62, 0.36, '#ffffff', 0.9); bayrak.position.set(0.3, 1.5, 0.35); g.add(bayrak);
    var cubuk = new T.Mesh(new T.CylinderGeometry(0.02, 0.02, 0.9, 6), laci); cubuk.position.set(0.0, 1.0, 0.3); g.add(cubuk);
    g.userData = { y0: 0, y1: 1.35, yari: 0.95 }; PROTO.burger = g;

    // Kruvasan (alçak)
    var k = new T.Group();
    var kr = new T.Mesh(new T.TorusGeometry(0.6, 0.3, 12, 24, Math.PI * 1.1), std(0xd9923c, { roughness: 0.7 }));
    kr.rotation.set(-Math.PI / 2, 0, Math.PI * 0.95); kr.position.y = 0.32; kr.scale.set(1.15, 1, 1); k.add(kr);
    for (var j = 0; j < 4; j++) { var ban = new T.Mesh(new T.TorusGeometry(0.31, 0.03, 6, 14), std(0xa8681f)); ban.position.set(-0.55 + j * 0.37, 0.34, -0.35 + (j % 2) * 0.05); ban.rotation.y = Math.PI / 2; k.add(ban); }
    var d3 = decal(0.7, 0.34, '#ffffff', 0.9); d3.position.set(0, 0.2, 0.7); k.add(d3);
    k.userData = { y0: 0, y1: 0.95, yari: 0.9 }; PROTO.kruvasan = k;

    // Espresso makinesi (uzun)
    var m = new T.Group();
    var gv = new T.Mesh(new T.BoxGeometry(1.7, 2.1, 1.3), std(0xc9d0de, { metalness: 0.05, roughness: 0.45, emissive: 0x333a4a, emissiveIntensity: 0.4 })); gv.position.y = 1.05; m.add(gv);
    var ust = new T.Mesh(new T.BoxGeometry(1.8, 0.2, 1.4), laci); ust.position.y = 2.2; m.add(ust);
    var pano = decal(1.4, 0.7, '#ffffff', 0.88); pano.position.set(0, 1.55, 0.66); m.add(pano);
    var dugme = new T.Mesh(new T.SphereGeometry(0.1, 10, 8), std(0xe0554b, { emissive: 0x801010 })); dugme.position.set(0.55, 0.95, 0.66); m.add(dugme);
    var kolu = new T.Mesh(new T.CylinderGeometry(0.09, 0.09, 0.5, 10), laci); kolu.rotation.x = Math.PI / 2; kolu.position.set(-0.3, 0.75, 0.85); m.add(kolu);
    m.userData = { y0: 0, y1: 2.35, yari: 0.8 }; PROTO.makine = m;

    // Asılı pankart (kay)
    var p = new T.Group();
    var dir1 = new T.Mesh(new T.CylinderGeometry(0.1, 0.12, 3.2, 10), laci); dir1.position.set(-1.6 * SERIT, 1.6, 0); p.add(dir1);
    var dir2 = dir1.clone(); dir2.position.x = 1.6 * SERIT; p.add(dir2);
    var bez = new T.Mesh(new T.PlaneGeometry(3.3 * SERIT, 1.15), new T.MeshBasicMaterial({ map: logoTexture('#ffe9bd', 1024, 360, 0.62), side: T.DoubleSide }));
    bez.position.set(0, 2.1, 0); p.add(bez);
    var kenar = new T.Mesh(new T.BoxGeometry(3.4 * SERIT, 0.08, 0.1), krem); kenar.position.set(0, 1.5, 0); p.add(kenar);
    p.userData = { y0: 1.45, y1: 3.0, yari: 1.0, tum: true }; PROTO.pankart = p;

    // Kahve çekirdeği
    var cek = new T.Group();
    var ck = new T.Mesh(new T.SphereGeometry(0.28, 14, 10), std(0x6b3a1c, { roughness: 0.35, emissive: 0x2a1204, emissiveIntensity: 0.4 })); ck.scale.set(0.72, 1, 0.55); cek.add(ck);
    var ciz = new T.Mesh(new T.TorusGeometry(0.2, 0.025, 6, 14, Math.PI), std(KREMA, { emissive: 0x7a5200, emissiveIntensity: 0.6 })); ciz.position.z = 0.15; ciz.rotation.z = Math.PI / 2; ciz.scale.set(0.6, 1.1, 1); cek.add(ciz);
    PROTO.cekirdek = cek;

    // Espresso gücü
    var e = new T.Group();
    var ec = new T.Mesh(new T.CylinderGeometry(0.32, 0.22, 0.42, 20), std(0xffffff, { emissive: 0x888888 })); e.add(ec);
    var etabak = new T.Mesh(new T.CylinderGeometry(0.42, 0.34, 0.06, 20), std(KREMA, { emissive: 0x7a5200 })); etabak.position.y = -0.24; e.add(etabak);
    var ekah = new T.Mesh(new T.CylinderGeometry(0.27, 0.27, 0.03, 20), std(0x6b3a1c, { emissive: 0x3a1a05 })); ekah.position.y = 0.21; e.add(ekah);
    var halka = new T.Mesh(new T.TorusGeometry(0.6, 0.035, 8, 28), new T.MeshBasicMaterial({ color: 0xffd36a })); halka.rotation.x = Math.PI / 2; e.add(halka);
    PROTO.guc = e;
  }

  /* ---- dünya: yol, binalar, lambalar, ağaçlar, ufuk ---- */
  function pencereDoku() {
    var cv = document.createElement('canvas'); cv.width = 128; cv.height = 128;
    var c = cv.getContext('2d'); c.fillStyle = '#fff'; c.fillRect(0, 0, 128, 128);
    var em = document.createElement('canvas'); em.width = 128; em.height = 128;
    var e = em.getContext('2d'); e.fillStyle = '#000'; e.fillRect(0, 0, 128, 128);
    for (var y = 0; y < 4; y++) for (var x = 0; x < 3; x++) {
      var px = 12 + x * 38, py = 10 + y * 30;
      c.fillStyle = '#7a8fb8'; c.fillRect(px, py, 24, 20);
      c.fillStyle = 'rgba(255,255,255,.55)'; c.fillRect(px, py, 24, 5);
      if ((x * 7 + y * 13 + (x * y)) % 3 !== 0) { e.fillStyle = '#fff'; e.fillRect(px, py, 24, 20); }
    }
    var t1 = new T.CanvasTexture(cv), t2 = new T.CanvasTexture(em);
    [t1, t2].forEach(function (t) { t.wrapS = t.wrapT = T.RepeatWrapping; });
    return [t1, t2];
  }

  function yolDokusu() {
    var cv = document.createElement('canvas'); cv.width = 256; cv.height = 256;
    var c = cv.getContext('2d');
    c.fillStyle = '#2b2f58'; c.fillRect(0, 0, 256, 256);
    // yol çizgileri: iki şerit ayracı
    c.fillStyle = '#f2b544';
    var w = 256 / 3;
    for (var i = 1; i < 3; i++) c.fillRect(i * w - 3, 20, 6, 90), c.fillRect(i * w - 3, 148, 6, 90);
    // ince doku
    c.fillStyle = 'rgba(255,255,255,.04)';
    for (var k = 0; k < 90; k++) c.fillRect(Math.random() * 256, Math.random() * 256, 2, 2);
    var t = new T.CanvasTexture(cv); t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 4;
    t.repeat.set(1, 18);
    return t;
  }

  function ufukDokusu() {
    var cv = document.createElement('canvas'); cv.width = 1024; cv.height = 128;
    var c = cv.getContext('2d'); c.fillStyle = '#fff';
    var x = 0;
    while (x < 1024) { var w = 24 + Math.random() * 50, h = 30 + Math.random() * 90; c.fillRect(x, 128 - h, w, h); x += w + Math.random() * 6; }
    var t = new T.CanvasTexture(cv); t.wrapS = T.RepeatWrapping; t.repeat.x = 2; return t;
  }

  var BINA_RENK = [0xfff1d6, 0xf6d7b0, 0xd9e4f5, 0xe9b8a0, 0xcfd6ea];
  function dunyaKur() {
    var pen = pencereDoku();
    dunya.binaMat = BINA_RENK.map(function (r) {
      return std(r, { map: pen[0], emissiveMap: pen[1], emissive: 0xffc860, emissiveIntensity: 0, roughness: 0.8 });
    });
    // yol
    dunya.yolDoku = yolDokusu();
    var yol = new T.Mesh(new T.PlaneGeometry(SERIT * 3, 400), std(0xffffff, { map: dunya.yolDoku, roughness: 0.85 }));
    yol.rotation.x = -Math.PI / 2; yol.position.z = -150; scene.add(yol);
    var kaldirimM = std(0xb3a98f, { roughness: 0.9 });
    [-1, 1].forEach(function (y) {
      var k = new T.Mesh(new T.BoxGeometry(5.5, 0.25, 400), kaldirimM); k.position.set(y * (SERIT * 1.5 + 2.9), -0.05, -150); scene.add(k);
      var bordur = new T.Mesh(new T.BoxGeometry(0.3, 0.32, 400), std(0x9aa0b4)); bordur.position.set(y * (SERIT * 1.5 + 0.1), 0.02, -150); scene.add(bordur);
    });
    // yan şerit dışı zemin
    var zemin = new T.Mesh(new T.PlaneGeometry(260, 400), std(0x6f7a5a, { roughness: 1 }));
    zemin.rotation.x = -Math.PI / 2; zemin.position.set(0, -0.2, -150); scene.add(zemin); dunya.zemin = zemin;

    // binalar
    dunya.binalar = [];
    var BAS = 260, adet = 15, adim = BAS / adet;
    var sablon = [[5, 9], [6, 14], [5, 6], [7, 11], [6, 8]];
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < adet; i++) {
        var grup = new T.Group();
        var s = sablon[(i * 3 + (yon > 0 ? 1 : 0)) % sablon.length];
        var gen = s[0], yuk = s[1], der = 8;
        var geo = new T.BoxGeometry(gen, yuk, der);
        var uv = geo.attributes.uv; for (var q = 0; q < uv.count; q++) uv.setXY(q, uv.getX(q) * gen / 2.4, uv.getY(q) * yuk / 3.2);
        var m = new T.Mesh(geo, dunya.binaMat[(i + (yon > 0 ? 2 : 0)) % dunya.binaMat.length]);
        m.position.y = yuk / 2; grup.add(m);
        var cati = new T.Mesh(new T.BoxGeometry(gen + 0.3, 0.3, der + 0.3), std(0x8c7b6b)); cati.position.y = yuk + 0.1; grup.add(cati);
        // tabela (her 2. binada)
        if (i % 2 === 0) {
          var tabela = new T.Mesh(new T.PlaneGeometry(3.6, 1.6), new T.MeshBasicMaterial({ map: logoTexture('#ffffff', 512, 228, 0.82) }));
          tabela.position.set(-yon * (gen / 2 + 0.05), 3.6, 0); tabela.rotation.y = -yon * Math.PI / 2; grup.add(tabela);
          var tente = new T.Mesh(new T.BoxGeometry(1.2, 0.12, 4.2), std(i % 4 === 0 ? 0xe0554b : KREMA)); tente.position.set(-yon * (gen / 2 + 0.55), 2.55, 0); tente.rotation.z = yon * 0.22; grup.add(tente);
        }
        grup.position.set(yon * (SERIT * 1.5 + 8.2 + gen / 2 + (i % 3) * 0.8), 0, -i * adim);
        scene.add(grup);
        dunya.binalar.push({ g: grup, z: -i * adim, yon: yon, gen: gen });
      }
    });
    dunya.binaBoy = BAS;

    // lambalar
    dunya.lambalar = [];
    var lampM = std(0x2b2f45), ampulM = new T.MeshBasicMaterial({ color: 0xffe2a0, transparent: true, opacity: 0.35 });
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < 14; i++) {
        var g = new T.Group();
        var dir = new T.Mesh(new T.CylinderGeometry(0.07, 0.1, 4.2, 8), lampM); dir.position.y = 2.1; g.add(dir);
        var kol = new T.Mesh(new T.BoxGeometry(1.1, 0.08, 0.08), lampM); kol.position.set(-yon * 0.55, 4.2, 0); g.add(kol);
        var amp = new T.Mesh(new T.SphereGeometry(0.2, 10, 8), ampulM.clone()); amp.position.set(-yon * 1.05, 4.1, 0); g.add(amp);
        g.position.set(yon * (SERIT * 1.5 + 0.9), 0, -i * 19);
        scene.add(g); dunya.lambalar.push({ g: g, z: -i * 19, amp: amp });
      }
    });
    dunya.lambaBoy = 14 * 19;

    // ağaçlar (kaldırımda)
    dunya.agaclar = [];
    [-1, 1].forEach(function (yon) {
      for (var i = 0; i < 8; i++) {
        var g = new T.Group();
        var govde = new T.Mesh(new T.CylinderGeometry(0.14, 0.2, 1.6, 8), std(0x6b4a2b)); govde.position.y = 0.8; g.add(govde);
        var yaprak = new T.Mesh(new T.SphereGeometry(0.8, 12, 10), std(0x4f9a52, { roughness: 0.9 })); yaprak.position.y = 2.2; yaprak.scale.y = 1.15; g.add(yaprak);
        g.position.set(yon * (SERIT * 1.5 + 2.4), 0, -i * 33 - 10);
        scene.add(g); dunya.agaclar.push({ g: g, z: -i * 33 - 10 });
      }
    });
    dunya.agacBoy = 8 * 33;

    // ufuk silüeti, güneş, ay
    dunya.ufukMat = new T.MeshBasicMaterial({ map: ufukDokusu(), color: 0xe9c488, transparent: true, fog: false, depthWrite: false });
    var ufuk = new T.Mesh(new T.PlaneGeometry(520, 60), dunya.ufukMat); ufuk.position.set(0, 26, -230); scene.add(ufuk);
    dunya.gunes = new T.Mesh(new T.CircleGeometry(16, 40), new T.MeshBasicMaterial({ color: 0xfff1b8, fog: false })); dunya.gunes.position.set(40, 40, -235); scene.add(dunya.gunes);
    dunya.ay = new T.Mesh(new T.CircleGeometry(8, 32), new T.MeshBasicMaterial({ color: 0xe8eeff, fog: false })); dunya.ay.position.set(-50, 60, -236); scene.add(dunya.ay);
    // yıldızlar
    var ys = new Float32Array(240 * 3);
    for (var s = 0; s < 240; s++) { ys[s * 3] = (Math.random() - 0.5) * 420; ys[s * 3 + 1] = 40 + Math.random() * 120; ys[s * 3 + 2] = -240; }
    var yg = new T.BufferGeometry(); yg.setAttribute('position', new T.BufferAttribute(ys, 3));
    dunya.yildiz = new T.Points(yg, new T.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0, fog: false }));
    scene.add(dunya.yildiz);
  }

  function gokGuncelle(mesafe) {
    var faz = (mesafe / 1400) % 1;                    // gündüz → akşam → gece → gündüz
    var a, b, t;
    if (faz < 0.35) { a = gokRenk.gun; b = gokRenk.gun; t = 0; }
    else if (faz < 0.55) { a = gokRenk.gun; b = gokRenk.aksam; t = (faz - 0.35) / 0.2; }
    else if (faz < 0.7) { a = gokRenk.aksam; b = gokRenk.gece; t = (faz - 0.55) / 0.15; }
    else if (faz < 0.85) { a = gokRenk.gece; b = gokRenk.gece; t = 0; }
    else { a = gokRenk.gece; b = gokRenk.gun; t = (faz - 0.85) / 0.15; }
    var gece = (faz >= 0.55 && faz < 0.85) ? (faz < 0.7 ? (faz - 0.55) / 0.15 : 1) : (faz >= 0.85 ? 1 - (faz - 0.85) / 0.15 : 0);
    dunya._renk = dunya._renk || new T.Color();
    dunya._renk.copy(a).lerp(b, t);
    scene.background.copy(dunya._renk); scene.fog.color.copy(dunya._renk);
    hemi.intensity = 0.95 - gece * 0.55; gunes.intensity = 0.85 - gece * 0.6;
    dunya.binaMat.forEach(function (m) { m.emissiveIntensity = gece * 1.1; });
    dunya.lambalar.forEach(function (l) { l.amp.material.opacity = 0.35 + gece * 0.65; });
    dunya.ufukMat.color.copy(dunya._renk).multiplyScalar(0.72);
    dunya.gunes.position.y = 40 - gece * 70; dunya.ay.position.y = 10 + gece * 50;
    dunya.yildiz.material.opacity = Math.max(0, gece - 0.3);
    dunya.zemin.material.color.setHex(0x6f7a5a).multiplyScalar(1 - gece * 0.6);
  }

  /* ---------- oyun mantığı ---------- */
  function sifirla() {
    // eski nesneleri temizle
    if (G) { G.engeller.forEach(function (o) { scene.remove(o.g); }); G.cekirdekler.forEach(function (o) { scene.remove(o.g); }); }
    G = {
      hiz: 0, hedefHiz: 14, mesafe: 0, sure: 0, skor: 0, cekirdek: 0, kombo: 0, komboZaman: 0,
      serit: 0, x: 0, y: 0, vy: 0, kayma: 0, yerde: true, ziplamaSayisi: 0,
      engeller: [], cekirdekler: [], spawnZ: -45, sonKirma: 0, guc: 0, gucToplam: 7,
      ol: false, olZaman: 0, sarsinti: 0, sonMesafeOdul: 0, ilkMesaj: true, sonSatirTipi: ''
    };
    parcaciklar.forEach(function (p) { p.m.visible = false; });
    oyuncu.grup.position.set(0, 0, 0); oyuncu.grup.rotation.set(0, 0, 0); oyuncu.kalkan.visible = false;
    hGucBar.parentNode.hidden = true;
  }

  function nesneAl(tip) {
    var g = PROTO[tip].clone(); g.visible = true; scene.add(g);
    return g;
  }

  function satirUret(hizRef) {
    var t = G.sure, mesafe = G.mesafe;
    var zorluk = Math.min(1, t / 90);
    var aralikSn = Math.max(0.85, 1.55 - t * 0.011) + Math.random() * 0.55;
    var aralik = Math.max(hizRef, 14) * aralikSn;
    if (G.sonSatirTipi === 'pankart') aralik *= 1.25;
    G.spawnZ -= aralik;
    var wz = G.spawnZ, sw = -(G.mesafe) + wz;           // dünya konumu (mesafe ile birlikte kayar)
    var r = Math.random(), tip, serit;
    var alcak = ['fincan', 'burger', 'kruvasan'], uzun = ['bardak', 'makine'];
    function ekle(tipAd, s) {
      var g = nesneAl(tipAd); var d = PROTO[tipAd].userData;
      G.engeller.push({ g: g, wz: wz, lane: s, tip: tipAd, y0: d.y0, y1: d.y1, tum: !!d.tum, kirik: false });
      g.position.set(s * SERIT, 0, 0);
    }
    var satir;
    if (t < 6) satir = 'bos';
    else if (r < 0.34) satir = 'alcak1';
    else if (r < 0.52) satir = 'alcak2';
    else if (r < 0.7 + zorluk * 0.05) satir = 'uzun1';
    else if (r < 0.82 + zorluk * 0.05) satir = 'uzun2';
    else if (r < 0.9) satir = 'pankart';
    else satir = 'alcakUzun';
    if (t < 14 && (satir === 'uzun2' || satir === 'pankart' || satir === 'alcakUzun')) satir = 'alcak1';
    G.sonSatirTipi = satir;
    var seritler = [-1, 0, 1].sort(function () { return Math.random() - 0.5; });
    var A = alcak[Math.floor(Math.random() * 3)], B = uzun[Math.floor(Math.random() * 2)];
    var bosSerit = seritler[2];
    if (satir === 'alcak1') ekle(A, seritler[0]);
    else if (satir === 'alcak2') { ekle(A, seritler[0]); ekle(alcak[Math.floor(Math.random() * 3)], seritler[1]); if (zorluk > 0.5 && Math.random() < 0.4) ekle(A, seritler[2]); }
    else if (satir === 'uzun1') { ekle(B, seritler[0]); }
    else if (satir === 'uzun2') { ekle(B, seritler[0]); ekle(uzun[Math.floor(Math.random() * 2)], seritler[1]); }
    else if (satir === 'alcakUzun') { ekle(B, seritler[0]); ekle(A, seritler[1]); }
    else if (satir === 'pankart') { ekle('pankart', 0); }
    // çekirdek yolu: engeller arasındaki boşlukta, boş şeritte
    if (Math.random() < 0.65 || satir === 'bos') {
      var cs = (satir === 'pankart' || satir === 'bos') ? seritler[Math.floor(Math.random() * 3)] : bosSerit;
      if (satir === 'alcak1') cs = Math.random() < 0.5 ? seritler[0] : bosSerit;
      var yay = (satir === 'alcak1' && cs === seritler[0]);
      var n = yay ? 7 : 6, oncekiWz = wz + aralik * 0.5;
      for (var i = 0; i < n; i++) {
        var cz = yay ? wz + (i - 3) * 1.4 : oncekiWz + (i - 2.5) * 1.8;
        var cy = yay ? 1.0 + Math.sin(i / (n - 1) * Math.PI) * 1.05 : 0.9;
        var cg = nesneAl('cekirdek'); cg.position.set(cs * SERIT, cy, 0);
        G.cekirdekler.push({ g: cg, wz: cz, lane: cs, y: cy, alindi: false });
      }
    }
    // nadiren espresso gücü
    if (t > 12 && Math.random() < 0.09 && !G.guc) {
      var gs = bosSerit, gg = nesneAl('guc'); gg.position.set(gs * SERIT, 1.1, 0);
      G.cekirdekler.push({ g: gg, wz: wz + aralik * 0.5, lane: gs, y: 1.1, alindi: false, guc: true });
    }
  }

  function mesaj(metin, ms) {
    hMesaj.textContent = metin; hMesaj.classList.add('goster');
    clearTimeout(mesaj._t); mesaj._t = setTimeout(function () { hMesaj.classList.remove('goster'); }, ms || 1400);
  }

  function parcacikPatlat(x, y, z, renk, adet, hizz) {
    for (var i = 0; i < adet; i++) {
      var p = parcaciklar.find(function (q) { return !q.m.visible; });
      if (!p) { if (parcaciklar.length > 90) return; p = { m: new T.Mesh(new T.BoxGeometry(0.14, 0.14, 0.14), new T.MeshBasicMaterial({ color: 0xffffff })), v: new T.Vector3(), omur: 0 }; scene.add(p.m); parcaciklar.push(p); }
      p.m.visible = true; p.m.material.color.setHex(renk[i % renk.length]);
      p.m.position.set(x, y, z); p.v.set((Math.random() - 0.5) * hizz, Math.random() * hizz * 0.9 + 1, (Math.random() - 0.5) * hizz);
      p.omur = 0.55 + Math.random() * 0.4; p.m.scale.setScalar(1);
    }
  }

  function seriteGit(yon) {
    var n = G.serit + yon;
    if (n < -1 || n > 1) return;
    G.serit = n; SES.serit();
  }
  function zipla() {
    if (G.yerde) { G.vy = ZIPLAMA_V; G.yerde = false; G.ziplamaSayisi = 1; G.kayma = 0; SES.ziplama(); }
    else if (G.ziplamaSayisi < 2 && G.vy < 4) { G.vy = ZIPLAMA_V * 0.82; G.ziplamaSayisi = 2; SES.ziplama(); parcacikPatlat(oyuncu.grup.position.x, G.y + 0.2, 0, [0xffffff, KREMA], 8, 3); }
  }
  function kay() {
    if (!G.yerde) G.vy = -20;
    G.kayma = 0.75; SES.kayma();
  }

  function bitir(neden) {
    G.ol = true; G.olZaman = 0; G.sarsinti = 0.7; durum = 'bitis';
    SES.carpma(); if (navigator.vibrate) { try { navigator.vibrate(120); } catch (e) {} }
    parcacikPatlat(oyuncu.grup.position.x, G.y + 1, 0, [MAVI, 0xffffff, KREMA, 0x5b3317], 40, 9);
    hGucBar.parentNode.hidden = true;
    var bitisSkor = Math.floor(G.skor);
    var yeni = bitisSkor > ENIYI;
    setTimeout(function () {
      $('kb-skor').textContent = bitisSkor;
      $('kb-detay').textContent = Math.floor(G.mesafe) + ' m · ' + G.cekirdek + ' çekirdek';
      $('kb-rekor').hidden = !yeni;
      if (yeni) ENIYI = bitisSkor;
      $('kb-sira').textContent = bitisSkor > 0 && G.sure >= 3 ? 'Skor kaydediliyor…' : '';
      elBitis.hidden = false;
      skorGonder(bitisSkor, Math.floor(G.sure));
    }, 900);
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

  function guncelle(dt) {
    var kl = oyuncu.grup;
    if (G.ol) {
      G.olZaman += dt; G.hiz *= Math.pow(0.02, dt);
      kl.rotation.x += dt * 4; kl.position.y += (G.olZaman < 0.3 ? 4 : -6) * dt; if (kl.position.y < 0) kl.position.y = 0;
      return;
    }
    G.sure += dt;
    // hız
    G.hedefHiz = Math.min(14 + G.sure * 0.27, 35) + (G.guc > 0 ? 7 : 0);
    G.hiz += (G.hedefHiz - G.hiz) * Math.min(1, dt * 1.2);
    G.mesafe += G.hiz * dt;
    G.skor += G.hiz * dt * (G.guc > 0 ? 2 : 1);
    if (G.guc > 0) { G.guc -= dt; if (G.guc <= 0) { oyuncu.kalkan.visible = false; hGucBar.parentNode.hidden = true; } else hGucBar.style.width = (G.guc / G.gucToplam * 100) + '%'; }
    if (G.mesafe - G.sonMesafeOdul >= 500) { G.sonMesafeOdul = Math.floor(G.mesafe / 500) * 500; mesaj(G.sonMesafeOdul + ' metre!', 1500); SES.mesafe(); }
    if (G.komboZaman > 0) { G.komboZaman -= dt; if (G.komboZaman <= 0) G.kombo = 0; }

    // oyuncu fiziği
    G.x += (G.serit * SERIT - G.x) * Math.min(1, dt * 15);
    if (!G.yerde) {
      G.vy -= YERCEKIMI * dt; G.y += G.vy * dt;
      if (G.y <= 0) { G.y = 0; G.vy = 0; G.yerde = true; G.ziplamaSayisi = 0; parcacikPatlat(G.x, 0.1, 0, [0xcfc6b4, 0xffffff], 5, 2.5); }
    }
    if (G.kayma > 0) G.kayma -= dt;
    var kayiyor = G.kayma > 0 && G.yerde;
    kl.position.set(G.x, G.y, 0);
    var kos = G.mesafe * 0.9, salinim = Math.sin(kos * 1.1);
    oyuncu.govde.position.y = (kayiyor ? 0.62 : 1.05) + (G.yerde && !kayiyor ? Math.abs(salinim) * 0.09 : 0);
    oyuncu.govde.scale.set(0.82, kayiyor ? 0.46 : 0.82, 0.82);
    oyuncu.govde.rotation.z = -(G.serit * SERIT - G.x) * 0.1;
    oyuncu.govde.rotation.x = kayiyor ? -0.6 : (G.yerde ? -0.12 : -0.2);
    var kosuyor = G.yerde && !kayiyor;
    oyuncu.ayakSol.position.z = kosuyor ? salinim * 0.42 : 0.15; oyuncu.ayakSag.position.z = kosuyor ? -salinim * 0.42 : -0.25;
    oyuncu.ayakSol.position.y = kosuyor ? Math.max(0, Math.cos(kos * 1.1)) * 0.25 : 0.12; oyuncu.ayakSag.position.y = kosuyor ? Math.max(0, -Math.cos(kos * 1.1)) * 0.25 : 0.2;
    oyuncu.elSol.position.set(-0.95, 1.0 + (kosuyor ? salinim * 0.12 : 0.25), kosuyor ? -salinim * 0.3 : 0);
    oyuncu.elSag.position.set(0.95, 1.0 + (kosuyor ? -salinim * 0.12 : 0.25), kosuyor ? salinim * 0.3 : 0);
    if (oyuncu.kalkan.visible) { var s = 1 + Math.sin(G.sure * 8) * 0.06; oyuncu.kalkan.scale.setScalar(s); }
    oyuncu.golge.position.x = G.x; var gs = Math.max(0.4, 1 - G.y * 0.2); oyuncu.golge.scale.setScalar(gs); oyuncu.golge.material.opacity = 0.28 * gs;

    // spawn
    while (G.spawnZ > -(G.mesafe + CIZIM_UZAK)) satirUret(G.hiz);

    // engeller
    var px0 = G.x - 0.42, px1 = G.x + 0.42, pyAlt = G.y, pyUst = G.y + (kayiyor ? 0.75 : 1.75);
    for (var i = G.engeller.length - 1; i >= 0; i--) {
      var o = G.engeller[i], z = o.wz + G.mesafe;
      o.g.position.z = z;
      if (z > 14) { scene.remove(o.g); G.engeller.splice(i, 1); continue; }
      if (o.kirik) { o.g.position.y += dt * 8; o.g.rotation.x += dt * 6; o.g.position.x += dt * 4; continue; }
      if (z > -1.05 && z < 1.05) {
        var cx0, cx1;
        if (o.tum) { cx0 = -999; cx1 = 999; } else { cx0 = o.lane * SERIT - 1.0; cx1 = o.lane * SERIT + 1.0; }
        if (px1 > cx0 && px0 < cx1 && pyUst > o.y0 && pyAlt < o.y1) {
          if (G.guc > 0) { o.kirik = true; SES.kirma(); G.sarsinti = 0.25; G.skor += 25; parcacikPatlat(o.g.position.x, 1, 0, [0xffffff, KREMA, 0x5b3317], 16, 8); }
          else { bitir(); return; }
        }
      }
    }
    // çekirdekler
    for (var j = G.cekirdekler.length - 1; j >= 0; j--) {
      var c = G.cekirdekler[j], cz = c.wz + G.mesafe;
      c.g.position.z = cz; c.g.rotation.y += dt * (c.guc ? 3 : 5);
      if (c.guc) c.g.position.y = 1.1 + Math.sin(G.sure * 4) * 0.12;
      if (cz > 12) { scene.remove(c.g); G.cekirdekler.splice(j, 1); continue; }
      if (!c.alindi && cz > -1.2 && cz < 1.2 && Math.abs(c.g.position.x - G.x) < 1.15 && Math.abs(c.y - (G.y + 0.9)) < 1.25) {
        c.alindi = true; scene.remove(c.g); G.cekirdekler.splice(j, 1);
        if (c.guc) {
          G.guc = G.gucToplam; oyuncu.kalkan.visible = true; hGucBar.parentNode.hidden = false; SES.guc(); mesaj('ESPRESSO! Çift puan, engelleri kır', 1800);
          parcacikPatlat(G.x, 1, 0, [0xffd36a, 0xffffff], 20, 7);
        } else {
          G.kombo++; G.komboZaman = 1.2; G.cekirdek++; G.skor += 5 * (G.guc > 0 ? 2 : 1); SES.cekirdek(G.kombo);
          parcacikPatlat(c.g.position.x, c.y, 0, [KREMA, 0xffffff], 4, 3);
        }
      }
    }
    // dünya kaydırma
    var d = G.hiz * dt;
    dunya.yolDoku.offset.y -= d / (400 / 18);
    dunya.binalar.forEach(function (b) { b.z += d; if (b.z > 30) b.z -= dunya.binaBoy; b.g.position.z = b.z; });
    dunya.lambalar.forEach(function (l) { l.z += d; if (l.z > 20) l.z -= dunya.lambaBoy; l.g.position.z = l.z; });
    dunya.agaclar.forEach(function (a) { a.z += d; if (a.z > 20) a.z -= dunya.agacBoy; a.g.position.z = a.z; });
    gokGuncelle(G.mesafe);

    // HUD
    hSkor.textContent = Math.floor(G.skor); hCekirdek.textContent = G.cekirdek;
    hHiz.textContent = 'x' + (G.hiz / 14).toFixed(1);
  }

  function kameraGuncelle(dt, gercek) {
    var dikey = innerWidth / innerHeight < 0.9;
    var hedefFov = (dikey ? 74 : 60) + (G && G.guc > 0 ? 8 : 0) + (G ? Math.min(G.hiz - 14, 20) * 0.25 : 0);
    kamera.fov += (hedefFov - kamera.fov) * Math.min(1, dt * 3); kamera.updateProjectionMatrix();
    var x = G ? G.x * 0.55 : 0, y = dikey ? 5.6 : 4.4, z = dikey ? 9.6 : 7.6;
    var sars = 0;
    if (G && G.sarsinti > 0) { G.sarsinti -= dt; sars = G.sarsinti; }
    kamera.position.set(x + (Math.random() - 0.5) * sars * 0.6, y + (G ? G.y * 0.25 : 0) + (Math.random() - 0.5) * sars * 0.6, z);
    kamera.lookAt(x * 0.8, 1.6, -12);
    if (G) kamera.rotation.z = -(G.serit * SERIT - G.x) * 0.012;
  }

  function parcacikGuncelle(dt) {
    parcaciklar.forEach(function (p) {
      if (!p.m.visible) return;
      p.omur -= dt; if (p.omur <= 0) { p.m.visible = false; return; }
      p.v.y -= 22 * dt; p.m.position.addScaledVector(p.v, dt); p.m.scale.setScalar(Math.max(0.1, p.omur * 1.6));
      p.m.rotation.x += dt * 8; p.m.rotation.y += dt * 6;
    });
  }

  /* ---------- döngü ---------- */
  var son = 0, raf = 0;
  function dongu(t) {
    raf = requestAnimationFrame(dongu);
    var dt = Math.min((t - son) / 1000, 0.05); son = t;
    if (durum === 'oyun' || durum === 'bitis') guncelle(dt);
    else if (durum === 'menu') {
      // menü arka planı: yavaşça akan dünya
      if (!G) sifirla();
      G.mesafe += 6 * dt; dunya.yolDoku.offset.y -= 6 * dt / (400 / 18);
      dunya.binalar.forEach(function (b) { b.z += 6 * dt; if (b.z > 30) b.z -= dunya.binaBoy; b.g.position.z = b.z; });
      dunya.lambalar.forEach(function (l) { l.z += 6 * dt; if (l.z > 20) l.z -= dunya.lambaBoy; l.g.position.z = l.z; });
      dunya.agaclar.forEach(function (a) { a.z += 6 * dt; if (a.z > 20) a.z -= dunya.agacBoy; a.g.position.z = a.z; });
      gokGuncelle(G.mesafe);
      oyuncu.grup.rotation.y = Math.sin(t / 900) * 0.35; oyuncu.grup.position.y = Math.abs(Math.sin(t / 380)) * 0.12;
    }
    parcacikGuncelle(dt);
    kameraGuncelle(dt);
    renderer.render(scene, kamera);
  }

  function boyutla() {
    if (!renderer) return;
    var w = elSahne.clientWidth || innerWidth, h = elSahne.clientHeight || innerHeight;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);
    kamera.aspect = w / h; kamera.updateProjectionMatrix();
  }

  function motorKur() {
    if (motorHazir) return;
    renderer = new T.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.domElement.className = 'kosu-cv';
    elSahne.appendChild(renderer.domElement);
    scene = new T.Scene(); scene.background = new T.Color(0xffe3a8); scene.fog = new T.Fog(0xffe3a8, 45, 175);
    kamera = new T.PerspectiveCamera(60, 1, 0.1, 320);
    hemi = new T.HemisphereLight(0xfff4dc, 0x7d8ca8, 0.95); scene.add(hemi);
    gunes = new T.DirectionalLight(0xfff0d0, 0.85); gunes.position.set(-6, 14, 8); scene.add(gunes);
    oyuncuKur(); protoKur(); dunyaKur();
    // çekirdek/güç prototipleri sahnede görünmesin
    motorHazir = true; boyutla();
    window.addEventListener('resize', boyutla);
    raf = requestAnimationFrame(function (t) { son = t; dongu(t); });
  }

  /* ---------- akış: aç / başla / duraklat / kapat ---------- */
  function tamEkran() {
    var e = kok;
    try { var f = e.requestFullscreen || e.webkitRequestFullscreen; if (f) { var p = f.call(e); if (p && p.catch) p.catch(function () {}); } } catch (x) {}
  }
  function tamEkrandanCik() {
    try { if (document.fullscreenElement || document.webkitFullscreenElement) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); } } catch (x) {}
  }

  function ac() {
    kok.hidden = false; document.documentElement.classList.add('kosu-acik');
    tamEkran(); sesBaslat();
    if (!motorHazir) { try { motorKur(); } catch (e) { kok.hidden = true; document.documentElement.classList.remove('kosu-acik'); alert('Bu cihazda 3B oyun başlatılamadı.'); return; } }
    else { boyutla(); }
    durum = 'menu'; sifirla(); kok.classList.add('menude'); elMenu.hidden = false; elBitis.hidden = true; elDur.hidden = true;
    setTimeout(boyutla, 120);
  }
  function kapat() {
    durum = 'menu'; kok.hidden = true; document.documentElement.classList.remove('kosu-acik');
    tamEkrandanCik();
    if (gonderildi) location.reload();
  }
  function basla() {
    sesBaslat(); sifirla(); kok.classList.remove('menude'); durum = 'oyun'; elMenu.hidden = true; elBitis.hidden = true; elDur.hidden = true;
    gonderildi = gonderildi;
    mesaj('Koş! ← → şerit · ↑ zıpla · ↓ kay', 2200);
  }
  function duraklat() {
    if (durum !== 'oyun') return; durum = 'dur'; elDur.hidden = false;
  }
  function surdur() { if (durum !== 'dur') return; elDur.hidden = true; durum = 'oyun'; son = performance.now(); }

  if (/kosudebug/.test(location.search)) window.__kosu = { g: function () { return G; } };

  /* ---------- girdiler ---------- */
  window.addEventListener('keydown', function (e) {
    if (kok.hidden) return;
    var k = e.code;
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Space'].indexOf(k) >= 0) e.preventDefault();
    if (e.repeat) return;
    if (durum === 'menu') { if (k === 'Space' || k === 'Enter') basla(); return; }
    if (durum === 'bitis') { if (G.ol && G.olZaman > 1.0 && (k === 'Space' || k === 'Enter')) basla(); return; }
    if (durum === 'dur') { if (k === 'KeyP' || k === 'Escape' || k === 'Space') surdur(); return; }
    if (k === 'ArrowLeft' || k === 'KeyA') seriteGit(-1);
    else if (k === 'ArrowRight' || k === 'KeyD') seriteGit(1);
    else if (k === 'ArrowUp' || k === 'KeyW' || k === 'Space') zipla();
    else if (k === 'ArrowDown' || k === 'KeyS') kay();
    else if (k === 'KeyP') duraklat();
  });

  var dok = null;
  elSahne.addEventListener('pointerdown', function (e) {
    if (durum !== 'oyun') return; dok = { x: e.clientX, y: e.clientY, t: performance.now(), tamam: false };
  });
  elSahne.addEventListener('pointermove', function (e) {
    if (!dok || dok.tamam || durum !== 'oyun') return;
    var dx = e.clientX - dok.x, dy = e.clientY - dok.y, esik = 28;
    if (Math.abs(dx) < esik && Math.abs(dy) < esik) return;
    dok.tamam = true;
    if (Math.abs(dx) > Math.abs(dy)) seriteGit(dx > 0 ? 1 : -1); else if (dy < 0) zipla(); else kay();
  });
  function dokBitir() {
    if (dok && !dok.tamam && durum === 'oyun' && performance.now() - dok.t < 260) zipla();
    dok = null;
  }
  elSahne.addEventListener('pointerup', dokBitir); elSahne.addEventListener('pointercancel', function () { dok = null; });
  elSahne.addEventListener('touchmove', function (e) { e.preventDefault(); }, { passive: false });

  document.addEventListener('visibilitychange', function () { if (document.hidden) duraklat(); });
  function tamEkranDegisti() {
    if (!kok.hidden && !(document.fullscreenElement || document.webkitFullscreenElement)) duraklat();
    setTimeout(boyutla, 80);
  }
  document.addEventListener('fullscreenchange', tamEkranDegisti); document.addEventListener('webkitfullscreenchange', tamEkranDegisti);

  /* düğmeler */
  [].forEach.call(document.querySelectorAll('[data-kosu-ac]'), function (b) { b.addEventListener('click', ac); });
  $('kosu-basla').addEventListener('click', basla);
  $('kosu-tekrar').addEventListener('click', basla);
  [].forEach.call(document.querySelectorAll('[data-kosu-kapat]'), function (b) { b.addEventListener('click', kapat); });
  $('kosu-duraklat').addEventListener('click', function () { if (durum === 'oyun') duraklat(); else if (durum === 'dur') surdur(); });
  $('kosu-devam').addEventListener('click', surdur);
  $('kosu-tam').addEventListener('click', function () { if (document.fullscreenElement || document.webkitFullscreenElement) tamEkrandanCik(); else tamEkran(); });
})();
