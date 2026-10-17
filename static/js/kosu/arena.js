/* Geek Oyun · Arena modu: dairesel Geek meydanında dalgalara karşı savaş.
   Çizim ve girdi burada; kurallar ECS sistemlerinde (sistemler.js). Koşu ile aynı karakter, dolap, yetenekler ve skor sistemini paylaşır. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var V = NS.veri, S = NS.sistemler;
  var R = 22;                         // oynanabilir yarıçap

  NS.arena = {
    kur: function (H) {
      var T = H.T, ui = H.ui;
      var A = { sahne: new T.Scene(), gece: 0.85, hazir: false };
      var sahne = A.sahne, W = null, oyuncu = null, vfx = null;
      var gorsel = {}, olenler = [], isik = {}, tazele = [];
      var durum = { sure: 0, oldurme: 0, enKombo: 0, faz: 0, kolAt: 0, atilmaIz: 0, bitti: false, yuzu: 0, ilkDalga: false, azCan: false };
      var raycaster = new T.Raycaster(), zemin = new T.Plane(new T.Vector3(0, 1, 0), 0), vv = new T.Vector3(), ndc = new T.Vector2();
      var imlecNokta = { x: 0, z: -8, var: false };
      var AYAK_GOLGE = null;

      /* ---------------- sahne ---------------- */
      function gokDokusu() {
        var cv = document.createElement('canvas'); cv.width = 8; cv.height = 256; var c = cv.getContext('2d');
        var g = c.createLinearGradient(0, 0, 0, 256);
        g.addColorStop(0, '#050b24'); g.addColorStop(0.45, '#0e2350'); g.addColorStop(0.78, '#3b4f93'); g.addColorStop(1, '#d98c64');
        c.fillStyle = g; c.fillRect(0, 0, 8, 256);
        var t = new T.CanvasTexture(cv); t.encoding = T.sRGBEncoding; return t;
      }
      function zeminDokusu() {
        var N = 1024, cv = document.createElement('canvas'); cv.width = cv.height = N; var c = cv.getContext('2d'), m = N / 2;
        c.fillStyle = '#c9ae7c'; c.fillRect(0, 0, N, N);
        // ahşap/taş döşeme: dairesel şeritlerde kısa tuğlalar
        for (var ring = 0; ring < 26; ring++) {
          var r0 = ring * (m / 26), r1 = (ring + 1) * (m / 26), adet = Math.max(6, Math.round(r1 * 6.2 / 24));
          for (var i = 0; i < adet; i++) {
            var a0 = i / adet * 6.2832 + ring * 0.13, a1 = (i + 0.94) / adet * 6.2832 + ring * 0.13, k = 0.82 + Math.random() * 0.2;
            c.fillStyle = 'rgb(' + Math.round(205 * k) + ',' + Math.round(176 * k) + ',' + Math.round(124 * k) + ')';
            c.beginPath(); c.arc(m, m, r1 - 1, a0, a1); c.arc(m, m, r0 + 1, a1, a0, true); c.closePath(); c.fill();
          }
        }
        // Geek mavisi halkalar ve yıldız çizgileri
        c.lineWidth = 9; c.strokeStyle = '#2a3bd6'; c.beginPath(); c.arc(m, m, m * 0.78, 0, 7); c.stroke();
        c.lineWidth = 4; c.strokeStyle = '#f9f3e5'; c.beginPath(); c.arc(m, m, m * 0.74, 0, 7); c.stroke(); c.beginPath(); c.arc(m, m, m * 0.82, 0, 7); c.stroke();
        c.lineWidth = 6; c.strokeStyle = 'rgba(42,59,214,.85)';
        for (var s = 0; s < 8; s++) { var an = s / 8 * 6.2832 + 0.39; c.beginPath(); c.moveTo(m + Math.cos(an) * m * 0.3, m + Math.sin(an) * m * 0.3); c.lineTo(m + Math.cos(an) * m * 0.72, m + Math.sin(an) * m * 0.72); c.stroke(); }
        c.fillStyle = '#d9cfb4'; c.beginPath(); c.arc(m, m, m * 0.26, 0, 7); c.fill();
        c.lineWidth = 8; c.strokeStyle = '#2a3bd6'; c.beginPath(); c.arc(m, m, m * 0.26, 0, 7); c.stroke();
        var t = new T.CanvasTexture(cv); t.encoding = T.sRGBEncoding; t.anisotropy = 8; return t;
      }
      function sahneKur() {
        sahne.background = gokDokusu();
        sahne.fog = new T.Fog(0x3b4f93, 55, 150);
        sahne.add(new T.HemisphereLight(0x9db0ff, 0x4a3a4a, 0.85));
        var ay = new T.DirectionalLight(0xc4d6ff, 1.25); ay.position.set(-10, 24, 8); ay.target.position.set(0, 0, 0); sahne.add(ay); sahne.add(ay.target);
        ay.castShadow = true; ay.shadow.mapSize.set(1536, 1536); var sc = ay.shadow.camera; sc.left = -20; sc.right = 20; sc.top = 20; sc.bottom = -20; sc.near = 1; sc.far = 70; ay.shadow.bias = -0.0005; ay.shadow.normalBias = 0.04;
        isik.ay = ay; A.isikAy = ay;
        var dolgu = new T.DirectionalLight(0xffb27a, 0.45); dolgu.position.set(12, 6, -14); sahne.add(dolgu);
        // zemin
        var zm = new T.Mesh(new T.CircleGeometry(R + 4, 96), new T.MeshStandardMaterial({ map: zeminDokusu(), roughness: 0.82, metalness: 0.02 })); zm.rotation.x = -Math.PI / 2; zm.receiveShadow = true; sahne.add(zm);
        var logo = new T.Mesh(new T.PlaneGeometry(6.4, 3.2), new T.MeshBasicMaterial({ map: H.logoTexture(null, 512, 256, 0.9, '#1b2a8f'), transparent: true, toneMapped: false, depthWrite: false })); logo.rotation.x = -Math.PI / 2; logo.position.y = 0.02; sahne.add(logo);
        var dis = new T.Mesh(new T.RingGeometry(R + 4, 90, 64), new T.MeshStandardMaterial({ color: 0x1a2142, roughness: 1 })); dis.rotation.x = -Math.PI / 2; dis.position.y = -0.05; sahne.add(dis);
        // sınır duvarı + çalılıklar
        var duvarM = new T.MeshStandardMaterial({ color: 0xf0e4c8, roughness: 0.7 }), duvarT = new T.MeshStandardMaterial({ color: 0x2a3bd6, roughness: 0.6 }), calM = new T.MeshStandardMaterial({ color: 0x3d8a52, roughness: 0.9 });
        var n = 56;
        for (var i = 0; i < n; i++) {
          var a = i / n * 6.2832, x = Math.cos(a) * (R + 1.2), z = Math.sin(a) * (R + 1.2);
          var blok = new T.Mesh(new T.BoxGeometry(2.7, 0.8, 0.9), duvarM); blok.position.set(x, 0.4, z); blok.rotation.y = -a + Math.PI / 2; blok.castShadow = true; blok.receiveShadow = true; sahne.add(blok);
          var serit = new T.Mesh(new T.BoxGeometry(2.72, 0.14, 0.94), duvarT); serit.position.set(x, 0.78, z); serit.rotation.y = blok.rotation.y; sahne.add(serit);
          if (i % 3 === 1) { var cali = new T.Mesh(new T.SphereGeometry(0.85, 12, 9), calM); cali.scale.set(1, 0.8, 1); cali.position.set(Math.cos(a) * (R + 2.4), 0.6, Math.sin(a) * (R + 2.4)); cali.castShadow = true; sahne.add(cali); }
        }
        // sokak lambaları (iç halkada)
        for (var l = 0; l < 6; l++) {
          var la = l / 6 * 6.2832 + 0.5, lx = Math.cos(la) * (R - 1.4), lz = Math.sin(la) * (R - 1.4);
          var dir = new T.Mesh(new T.CylinderGeometry(0.1, 0.14, 4.4, 10), new T.MeshStandardMaterial({ color: 0x0b0f2e, roughness: 0.5, metalness: 0.4 })); dir.position.set(lx, 2.2, lz); dir.castShadow = true; sahne.add(dir);
          var amp = new T.Mesh(new T.SphereGeometry(0.34, 14, 10), new T.MeshBasicMaterial({ color: 0xffe2a8, toneMapped: false })); amp.position.set(lx, 4.55, lz); sahne.add(amp);
          var p = H.parlama(0xffc766, 5.2, 0.8); p.position.set(lx, 4.55, lz); sahne.add(p);
          var havuz = new T.Mesh(new T.CircleGeometry(4.6, 32), new T.MeshBasicMaterial({ map: H.parlamaDokusu(), color: 0xffb860, transparent: true, opacity: 0.35, blending: T.AdditiveBlending, depthWrite: false })); havuz.rotation.x = -Math.PI / 2; havuz.position.set(lx, 0.04, lz); sahne.add(havuz);
        }
        // arka kemer + pankart (kamera -z'ye bakar)
        var kemer = new T.Group();
        [-1, 1].forEach(function (sx) { var d = new T.Mesh(new T.BoxGeometry(1.4, 9, 1.4), new T.MeshStandardMaterial({ color: 0x0b0f2e, roughness: 0.5 })); d.position.set(sx * 7.4, 4.5, 0); d.castShadow = true; kemer.add(d); });
        var ust = new T.Mesh(new T.BoxGeometry(17, 1.3, 1.5), new T.MeshStandardMaterial({ color: 0x2a3bd6, roughness: 0.5 })); ust.position.y = 9.2; kemer.add(ust);
        var pano = new T.Mesh(new T.PlaneGeometry(13.5, 3.4), new T.MeshBasicMaterial({ map: H.logoTexture('#0b0f2e', 1024, 256, 0.55, '#ffe9bd'), toneMapped: false })); pano.position.set(0, 9.2, 0.78); kemer.add(pano);
        var neon = new T.Mesh(new T.TorusGeometry(7.2, 0.08, 8, 48, Math.PI), new T.MeshBasicMaterial({ color: 0xffcf0b, toneMapped: false })); neon.position.y = 8.55; kemer.add(neon);
        kemer.position.set(0, 0, -(R + 5.5)); sahne.add(kemer);
        [[-4, 17, 0.1], [5, 18, -0.2], [-17, 10, 1.1], [17, 12, -1.2]].forEach(function (b) { var bg = bankModel(); bg.position.set(b[0], 0, b[1]); bg.rotation.y = Math.PI + b[2]; sahne.add(bg); });
        // gökyüzü: yıldızlar, ay, şehir silueti
        var yp = new Float32Array(420 * 3);
        for (var y = 0; y < 420; y++) { var th = Math.random() * 6.28, ph = Math.random() * 1.2 + 0.1, rr = 220; yp[y * 3] = Math.cos(th) * Math.cos(ph) * rr; yp[y * 3 + 1] = Math.sin(ph) * rr * 0.8 + 20; yp[y * 3 + 2] = Math.sin(th) * Math.cos(ph) * rr; }
        var yg = new T.BufferGeometry(); yg.setAttribute('position', new T.BufferAttribute(yp, 3));
        sahne.add(new T.Points(yg, new T.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0.85, fog: false })));
        var aySpr = H.parlama(0xe6eeff, 40, 0.95); aySpr.position.set(-70, 80, -160); sahne.add(aySpr);
        var pen = H.pencereDoku(); pen[0].repeat.set(3, 4); pen[1].repeat.set(3, 4);
        var binaM = new T.MeshStandardMaterial({ color: 0x3a4a80, map: pen[0], roughness: 0.9, emissive: 0xffd9a0, emissiveMap: pen[1], emissiveIntensity: 0.9 });
        for (var b = 0; b < 34; b++) {
          var ba = b / 34 * 6.2832 + Math.random() * 0.15, br = 62 + Math.random() * 30, bh = 12 + Math.random() * 30;
          var bi = new T.Mesh(new T.BoxGeometry(8 + Math.random() * 8, bh, 8 + Math.random() * 8), binaM); bi.position.set(Math.cos(ba) * br, bh / 2 - 0.05, Math.sin(ba) * br); sahne.add(bi);
        }
        A.hazir = true;
      }

      /* ---------------- yapılar (prop modelleri) ---------------- */
      function sandikModel() {
        var g = new T.Group(), ah = new T.MeshStandardMaterial({ color: 0x8a5a2c, roughness: 0.7 }), koyu = new T.MeshStandardMaterial({ color: 0x4a2c14, roughness: 0.8 });
        var govde = new T.Mesh(new T.BoxGeometry(1.5, 0.95, 1.1), ah); govde.position.y = 0.48; g.add(govde);
        [[-0.7, 0.48, 0.52], [0.7, 0.48, 0.52], [-0.7, 0.48, -0.52], [0.7, 0.48, -0.52]].forEach(function (p) { var d = new T.Mesh(new T.BoxGeometry(0.12, 1.0, 0.12), koyu); d.position.set(p[0], p[1], p[2]); g.add(d); });
        var kapak = new T.Mesh(new T.CylinderGeometry(0.58, 0.58, 1.5, 12, 1, false, 0, Math.PI), ah); kapak.rotation.z = Math.PI / 2; kapak.rotation.y = Math.PI / 2; kapak.position.y = 0.96; kapak.scale.set(1, 1, 1); g.add(kapak);
        var logo = new T.Mesh(new T.PlaneGeometry(0.9, 0.5), new T.MeshBasicMaterial({ map: H.logoTexture('#f9f3e5', 256, 144, 0.85), toneMapped: false })); logo.position.set(0, 0.5, 0.56); g.add(logo);
        H.golgeli(g, true, true); return g;
      }
      function ocakModel() {
        var g = new T.Group(), tas = new T.MeshStandardMaterial({ color: 0x3a3f55, roughness: 0.85 });
        var kase = new T.Mesh(new T.CylinderGeometry(1.0, 0.7, 0.8, 16), tas); kase.position.y = 1.0; kase.castShadow = true; g.add(kase);
        var ayak = new T.Mesh(new T.CylinderGeometry(0.22, 0.4, 0.8, 10), tas); ayak.position.y = 0.4; g.add(ayak);
        var kor = new T.Mesh(new T.CylinderGeometry(0.85, 0.85, 0.05, 16), new T.MeshBasicMaterial({ color: 0xff7a2a, toneMapped: false })); kor.position.y = 1.38; g.add(kor);
        var alev = H.parlama(0xff9a3a, 3.6, 0.95); alev.position.y = 2.1; g.add(alev); var alev2 = H.parlama(0xffd36a, 2.0, 0.9); alev2.position.y = 1.7; g.add(alev2);
        g.userData = { alev: alev, alev2: alev2 };
        var l = new T.PointLight(0xff8a3a, 2.2, 15, 1.6); l.position.y = 2.2; g.add(l); g.userData.isik = l;
        return g;
      }
      function sunakModel() {
        var g = new T.Group(), tas = new T.MeshStandardMaterial({ color: 0x59607e, roughness: 0.7 });
        var t1 = new T.Mesh(new T.CylinderGeometry(1.3, 1.5, 0.35, 8), tas); t1.position.y = 0.18; g.add(t1);
        var t2 = new T.Mesh(new T.CylinderGeometry(0.8, 1.05, 1.0, 8), tas); t2.position.y = 0.85; t2.castShadow = true; g.add(t2);
        var yuz = new T.Mesh(new T.CylinderGeometry(0.95, 0.85, 0.12, 8), new T.MeshStandardMaterial({ color: 0x2a3bd6, roughness: 0.4, emissive: 0x1b2a8f, emissiveIntensity: 0.6 })); yuz.position.y = 1.42; g.add(yuz);
        var kure = new T.Mesh(new T.IcosahedronGeometry(0.34, 1), new T.MeshBasicMaterial({ color: 0x8fb4ff, toneMapped: false })); kure.position.y = 2.2; g.add(kure);
        var halka = new T.Mesh(new T.TorusGeometry(0.62, 0.035, 8, 40), new T.MeshBasicMaterial({ color: 0xffcf0b, toneMapped: false })); halka.position.y = 2.2; halka.rotation.x = Math.PI / 2.4; g.add(halka);
        var p = H.parlama(0x6f9cff, 4, 0.8); p.position.y = 2.2; g.add(p);
        var l = new T.PointLight(0x6f9cff, 1.6, 12, 1.6); l.position.y = 2.4; g.add(l);
        g.userData = { kure: kure, halka: halka, p: p, isik: l };
        return g;
      }
      function bankModel() {
        var g = new T.Group(), ah = new T.MeshStandardMaterial({ color: 0xa87642, roughness: 0.7 }), met = new T.MeshStandardMaterial({ color: 0x0b0f2e, roughness: 0.5 });
        var oturak = new T.Mesh(new T.BoxGeometry(2.6, 0.12, 0.8), ah); oturak.position.y = 0.55; g.add(oturak);
        var sirt = new T.Mesh(new T.BoxGeometry(2.6, 0.6, 0.1), ah); sirt.position.set(0, 1.0, -0.38); sirt.rotation.x = -0.12; g.add(sirt);
        [-1.1, 1.1].forEach(function (x) { var a = new T.Mesh(new T.BoxGeometry(0.1, 0.6, 0.7), met); a.position.set(x, 0.28, 0); g.add(a); });
        H.golgeli(g, true, true); return g;
      }

      /* ---------------- düşman modelleri ---------------- */
      var JOLE_RENK = [0xcfe7ff, 0xdcb890, 0xb9e4a8, 0xffc9de];
      function gozler(g, y, z, ayr, olc, kizgin) {
        [-1, 1].forEach(function (s) {
          var beyaz = new T.Mesh(new T.SphereGeometry(0.2 * olc, 12, 10), new T.MeshStandardMaterial({ color: 0xffffff, roughness: 0.3 })); beyaz.position.set(s * ayr, y, z); g.add(beyaz);
          var bebek = new T.Mesh(new T.SphereGeometry(0.1 * olc, 10, 8), new T.MeshStandardMaterial({ color: 0x0b0f1c, roughness: 0.2 })); bebek.position.set(s * ayr, y - 0.01, z + 0.15 * olc); g.add(bebek);
          if (kizgin) { var kas = new T.Mesh(new T.BoxGeometry(0.32 * olc, 0.06 * olc, 0.05), new T.MeshStandardMaterial({ color: 0x1a1208 })); kas.position.set(s * ayr, y + 0.22 * olc, z + 0.1 * olc); kas.rotation.z = -s * 0.45; g.add(kas); }
        });
      }
      function joleModel(kral, tint) {
        var g = new T.Group(), mat = new T.MeshStandardMaterial({ color: tint, roughness: 0.12, metalness: 0, transparent: true, opacity: 0.84, emissive: tint, emissiveIntensity: 0.18, depthWrite: false });
        var govde = new T.Mesh(new T.SphereGeometry(1, 28, 20), mat); govde.scale.set(1, 0.84, 1); govde.position.y = 0.84; g.add(govde);
        var cek = new T.Mesh(new T.SphereGeometry(0.34, 14, 10), new T.MeshStandardMaterial({ color: 0x5b3317, roughness: 0.35, emissive: 0x2a1004, emissiveIntensity: 0.5 })); cek.scale.set(0.8, 1, 0.6); cek.position.set(0.2, 0.7, -0.15); g.add(cek);
        var yuz = new T.Group(); yuz.position.y = 0.9; g.add(yuz); gozler(yuz, 0, 0.78, 0.34, 1, kral);
        var agiz = new T.Mesh(new T.TorusGeometry(0.16, 0.025, 6, 14, Math.PI), new T.MeshBasicMaterial({ color: 0x3a2433 }), 0, 0, 0); agiz.position.set(0, -0.2, 0.9); agiz.rotation.z = Math.PI; yuz.add(agiz);
        var sprite = null;
        if (kral) {
          var tacM = new T.MeshStandardMaterial({ color: 0xf2b544, roughness: 0.25, metalness: 0.7, emissive: 0x6a4500, emissiveIntensity: 0.7 }), tac = new T.Group();
          var band = new T.Mesh(new T.CylinderGeometry(0.62, 0.7, 0.2, 18), tacM); tac.add(band);
          for (var i = 0; i < 7; i++) { var a = i / 7 * 6.2832, sp = new T.Mesh(new T.ConeGeometry(0.12, 0.45, 8), tacM); sp.position.set(Math.cos(a) * 0.62, 0.3, Math.sin(a) * 0.62); tac.add(sp); var m = new T.Mesh(new T.SphereGeometry(0.06, 8, 6), new T.MeshBasicMaterial({ color: i % 2 ? 0xe0554b : 0x6fc3ff, toneMapped: false })); m.position.set(Math.cos(a) * 0.62, 0.56, Math.sin(a) * 0.62); tac.add(m); }
          tac.position.set(0, 1.62, 0); tac.rotation.x = -0.08; g.add(tac);
          var cekler = new T.Group(); g.add(cekler);
          for (var j = 0; j < 8; j++) { var cb = new T.Mesh(new T.SphereGeometry(0.14, 10, 8), new T.MeshStandardMaterial({ color: 0x6b3a1c, roughness: 0.3, emissive: 0x3a1a05, emissiveIntensity: 0.6 })); cb.scale.set(0.75, 1, 0.55); cb.userData.a = j / 8 * 6.2832; cekler.add(cb); }
          g.userData.cekler = cekler;
        }
        g.userData.govde = govde; g.userData.mat = mat; g.userData.tip = kral ? 'kral' : 'jole'; g.userData.yuz = yuz;
        g.userData.tabanEmis = 0.18;
        return g;
      }
      function goblinModel() {
        var g = new T.Group(), deri = new T.MeshStandardMaterial({ color: 0x6fae4a, roughness: 0.6, emissive: 0x1a3a0a, emissiveIntensity: 0.15 }), tunik = new T.MeshStandardMaterial({ color: 0x7a4a24, roughness: 0.85 });
        var govde = new T.Group(); govde.position.y = 0.7; g.add(govde);
        var gv = new T.Mesh(new T.CylinderGeometry(0.34, 0.28, 0.7, 14), tunik); gv.position.y = 0.3; govde.add(gv);
        var kemer = new T.Mesh(new T.CylinderGeometry(0.35, 0.35, 0.09, 14), new T.MeshStandardMaterial({ color: 0x2a1a0c })); kemer.position.y = 0.1; govde.add(kemer);
        var bas = new T.Group(); bas.position.y = 0.95; govde.add(bas);
        var kafa = new T.Mesh(new T.SphereGeometry(0.34, 18, 14), deri); kafa.scale.set(1.1, 0.95, 1); bas.add(kafa);
        [-1, 1].forEach(function (s) { var kulak = new T.Mesh(new T.ConeGeometry(0.13, 0.55, 8), deri); kulak.position.set(s * 0.43, 0.05, 0); kulak.rotation.z = -s * 1.35; bas.add(kulak); });
        var burun = new T.Mesh(new T.ConeGeometry(0.09, 0.28, 8), deri); burun.position.set(0, -0.04, 0.4); burun.rotation.x = Math.PI / 2; bas.add(burun);
        [-1, 1].forEach(function (s) {
          var gz = new T.Mesh(new T.SphereGeometry(0.09, 10, 8), new T.MeshBasicMaterial({ color: 0xffe14a, toneMapped: false })); gz.position.set(s * 0.15, 0.08, 0.3); bas.add(gz);
          var bb = new T.Mesh(new T.SphereGeometry(0.04, 8, 6), new T.MeshBasicMaterial({ color: 0x1a0a00 })); bb.position.set(s * 0.15, 0.08, 0.375); bas.add(bb);
          var kas = new T.Mesh(new T.BoxGeometry(0.17, 0.04, 0.04), new T.MeshStandardMaterial({ color: 0x20300f })); kas.position.set(s * 0.15, 0.2, 0.33); kas.rotation.z = -s * 0.4; bas.add(kas);
        });
        var kruvM = new T.MeshStandardMaterial({ color: 0xe0a24e, roughness: 0.5, emissive: 0x4a2a08, emissiveIntensity: 0.3 });
        var kruv = new T.Mesh(new T.TorusGeometry(0.34, 0.14, 10, 22, Math.PI * 1.15), kruvM); kruv.position.set(0, 0.2, 0); kruv.rotation.set(Math.PI / 2 - 0.2, 0, Math.PI * 0.92 - Math.PI * 0.575 + 0.0); bas.add(kruv);
        function kol(s) {
          var omz = new T.Group(); omz.position.set(s * 0.4, 0.55, 0); govde.add(omz);
          var ust = new T.Mesh(new T.CylinderGeometry(0.075, 0.07, 0.55, 8), deri); ust.position.y = -0.24; omz.add(ust);
          return omz;
        }
        var kS = kol(-1), kD = kol(1);
        var sopa = new T.Group(); sopa.position.set(0, -0.5, 0.05); kD.add(sopa);
        var sp1 = new T.Mesh(new T.CylinderGeometry(0.08, 0.1, 0.9, 8), new T.MeshStandardMaterial({ color: 0xa87642, roughness: 0.7 })); sp1.position.y = 0.35; sopa.add(sp1);
        var sp2 = new T.Mesh(new T.CylinderGeometry(0.17, 0.17, 0.4, 10), new T.MeshStandardMaterial({ color: 0xa87642, roughness: 0.7 })); sp2.position.y = 0.72; sopa.add(sp2);
        function bacak(s) { var b = new T.Group(); b.position.set(s * 0.15, 0.02, 0); govde.add(b); var ba = new T.Mesh(new T.CylinderGeometry(0.09, 0.08, 0.55, 8), deri); ba.position.y = -0.27; b.add(ba); var ay = new T.Mesh(new T.BoxGeometry(0.2, 0.1, 0.34), new T.MeshStandardMaterial({ color: 0x2a1a0c })); ay.position.set(0, -0.55, 0.05); b.add(ay); return b; }
        var bS = bacak(-1), bD = bacak(1);
        g.userData = { tip: 'goblin', govde: govde, bas: bas, kS: kS, kD: kD, bS: bS, bD: bD, mat: deri, tabanEmis: 0.15 };
        g.scale.setScalar(1.05);
        H.golgeli(g, true, false);
        return g;
      }

      function dusmanGorseliYarat(e) {
        var tip = e.c.C_YZ.tip, g;
        if (tip === 'goblin') g = goblinModel();
        else if (tip === 'kral') { g = joleModel(true, 0xb9d6ff); g.scale.setScalar(V.DUSMAN.kral.r / 1.0 * 1.0); }
        else { g = joleModel(false, JOLE_RENK[Math.floor(Math.random() * JOLE_RENK.length)]); g.scale.setScalar(V.DUSMAN.jole.r / 0.75 * 0.78); }
        if (g.userData.govde && tip !== 'goblin') g.traverse(function (m) { if (m.isMesh) m.castShadow = true; });
        g.userData.faz = Math.random() * 6; g.userData.flas = 0; g.userData.olcek = g.scale.x;
        sahne.add(g); gorsel[e.id] = { g: g, tip: tip, e: e };
        var p = e.c.C_Transform; g.position.set(p.x, 0, p.z);
        // doğuş efekti
        H.parcacikPatlat(p.x, 0.4, p.z, [0x9db0ff, 0xffffff], 8, 5);
      }

      function toplanirGorseli(e) {
        var t = e.c.C_Toplanir, g = H.proto(t.tur === 'kalp' ? 'kalp' : 'cekirdek');
        if (!g) return;
        g.scale.setScalar(t.tur === 'kalp' ? 1.1 : 1.0);
        sahne.add(g); gorsel[e.id] = { g: g, tip: 'toplanir', e: e };
      }

      /* ---------------- dünya kurulumu ---------------- */
      function baslat() {
        if (!A.hazir) sahneKur();
        temizleDunya();
        W = new NS.Dunya('arena'); S.kur(W, { sinirR: R });
        var o = W.olustur('oyuncu', { x: 0, z: 4, ozellik: { etherRegen: 3.5, canRegen: 1.2, yara: 0.55 } });
        oyuncu = o; A.oyuncu = o;
        durum = { sure: 0, oldurme: 0, enKombo: 0, faz: 0, kolAt: 0, atilmaIz: 0, bitti: false, yuzu: 0, ilkDalga: false, azCan: false, geri: 3.0, geriSon: 99, atisT: 0 };
        // yapılar
        var sandiklar = [[-9, -9], [10, -11], [-3, 12], [13, 8]];
        sandiklar.forEach(function (p) { var e = W.olustur('prop', { tip: 'sandik', x: p[0], z: p[1], r: 0.95 }); var g = sandikModel(); g.position.set(p[0], 0, p[1]); g.rotation.y = Math.random() * 6; sahne.add(g); gorsel[e.id] = { g: g, tip: 'sandik', e: e }; });
        var oc = W.olustur('prop', { tip: 'ocak', x: -15, z: -4, r: 1.0 }); var og = ocakModel(); og.position.set(-15, 0, -4); sahne.add(og); gorsel[oc.id] = { g: og, tip: 'ocak', e: oc };
        var su = W.olustur('prop', { tip: 'sunak', x: 15, z: -4, r: 1.2 }); var sg = sunakModel(); sg.position.set(15, 0, -4); sahne.add(sg); gorsel[su.id] = { g: sg, tip: 'sunak', e: su };
        // gözlemciler
        W.on('varlik_dogdu', function (e) { if (e.c.C_YZ) dusmanGorseliYarat(e); else if (e.c.C_Toplanir) toplanirGorseli(e); });
        W.on('varlik_oldu', function (e) { var o2 = gorsel[e.id]; if (o2) { sahne.remove(o2.g); delete gorsel[e.id]; } });
        W.on('olum', olumGorseli);
        W.on('hasar_uygulandi', function (e) {
          if (e.hedef.c.C_Oyuncu) {
            if (e.miktar > 0) { ui.yarali(); H.sars(0.5); H.titre(40); H.SES.hasarAl && H.SES.hasarAl(); }
          } else { var g = gorsel[e.hedef.id]; if (g) g.g.userData.flas = 0.14; }
        });
        W.on('cast', function (c) {
          if (c.kaynak !== oyuncu) return;
          durum.kolAt = 0.28;
          if (c.id === 'dash') { H.parcacikPatlat(oyuncu.c.C_Transform.x, 0.6, oyuncu.c.C_Transform.z, [0x55dd63, 0xffffff], 12, 6); H.titre(15); }
          if (c.id !== 'atis') ui.gunluk(c.y.ad, '');
        });
        W.on('cast_reddedildi', function (c) {
          if (c.kaynak !== oyuncu || c.id === 'atis') return;
          if (c.neden === 'ether') { ui.mesaj('Ether yetersiz', 700); } else if (c.neden === 'dayaniklilik') ui.mesaj('Dayanıklılık yetersiz', 700);
          H.SES.red && H.SES.red();
        });
        W.on('toplandi', function (t) { H.SES.toplan && H.SES.toplan(t.tur); H.parcacikPatlat(t.x, 0.8, t.z, [t.tur === 'kalp' ? 0xdd5555 : 0x5599ff, 0xffffff], 6, 4); if (t.tur === 'kalp') ui.gunluk('+' + Math.round(t.deger) + ' can', 'iyi'); });
        W.on('puan', function (p) {
          if (!p.taban) return; vfx.sayiAt(p.x, 2.6, p.z, '+' + p.deger, 'puan'); if (p.kombo > durum.enKombo) durum.enKombo = p.kombo;
        });
        W.on('dalga_basladi', function (d) {
          ui.mesaj(d.boss ? 'PATRON GELİYOR!' : 'DALGA ' + d.no, 2000, true); ui.gunluk('Dalga ' + d.no + ' başladı · ' + d.adet + ' düşman', d.boss ? 'kotu' : ''); H.SES.dalga && H.SES.dalga(d.boss); H.flas(d.boss ? '#ff9a8a' : '#cfe0ff');
        });
        W.on('dalga_bitti', function (d) { ui.mesaj('Dalga temizlendi  +' + d.bonus, 1800); ui.gunluk('Dalga ' + d.no + ' temizlendi +' + d.bonus, 'puan'); H.SES.seviye && H.SES.seviye(); H.titre([20, 30, 20]); });
        W.on('dusman_dogur', function () { ui.mesaj('Kral Jöle yavru çağırdı!', 1400); });
        W.on('sunak_kullanildi', function (e) { ui.mesaj('Geek Gücü! Hasar x1,5 · 20 sn', 1800, true); H.parcacikPatlat(e.x, 1.5, e.z, [0x8fb4ff, 0xffcf0b, 0xffffff], 36, 9); H.flas('#c9d8ff'); H.SES.guc && H.SES.guc(); });
        W.on('kalkan_acildi', function () { ui.gunluk('Köpük Kalkan açıldı', 'iyi'); });
        W.on('kalkan_kirildi', function (e) { if (e.hedef === oyuncu) { ui.gunluk('Kalkan kırıldı', 'kotu'); H.parcacikPatlat(oyuncu.c.C_Transform.x, 1.2, oyuncu.c.C_Transform.z, [0xbfeaff, 0xffffff], 20, 8); } });
        W.on('oyuncu_oldu', function () { durum.bitti = true; H.arenaBitti(); });
        W.on('fark_etti', function () {});
        vfx = H.vfx; vfx.temizle(); vfx.bagla(W, sahne);
        H.B.grup.position.set(0, 0, 4); H.B.grup.rotation.set(0, Math.PI, 0);
        imlecNokta.var = false;
        ui.guclariSifirla();
        ui.geri('');
      }
      function temizleDunya() {
        for (var id in gorsel) sahne.remove(gorsel[id].g);
        gorsel = {}; olenler.forEach(function (o) { sahne.remove(o.g); }); olenler = [];
        if (vfx) vfx.temizle();
      }
      function olumGorseli(e) {
        var v = e.varlik, o = gorsel[v.id];
        if (!o) return;
        var p = v.c.C_Transform;
        if (v.c.C_YZ) {
          durum.oldurme++;
          H.SES.oldur && H.SES.oldur(o.tip === 'kral');
          H.parcacikPatlat(p.x, 0.8, p.z, o.tip === 'goblin' ? [0x6fae4a, 0xe0a24e, 0xffffff] : [0xcfe7ff, 0xffffff, 0x5b3317], o.tip === 'kral' ? 60 : 20, o.tip === 'kral' ? 14 : 8);
          if (o.tip === 'kral') { H.sars(1.2); H.flas('#ffe9a8'); H.titre([60, 40, 90]); ui.mesaj('Kral Jöle yenildi!', 2200, true); }
          ui.gunluk(V.DUSMAN[v.c.C_YZ.tip].ad + ' yenildi', 'puan');
          delete gorsel[v.id]; olenler.push({ g: o.g, t: 0, tip: o.tip });
        } else if (o.tip === 'sandik') {
          H.parcacikPatlat(p.x, 0.8, p.z, [0xa87642, 0x4a2c14, 0xf9f3e5], 24, 9); H.SES.kirma && H.SES.kirma(); ui.gunluk('Kahve sandığı kırıldı', 'iyi');
          delete gorsel[v.id]; sahne.remove(o.g);
        }
      }
      function olenleriGuncelle(dt) {
        for (var i = olenler.length - 1; i >= 0; i--) {
          var o = olenler[i]; o.t += dt;
          var k = Math.min(1, o.t / 0.5), base = o.g.userData.olcek || 1;
          o.g.scale.set(base * (1 + k * 0.5), base * Math.max(0.02, 1 - k), base * (1 + k * 0.5));
          if (o.g.userData.mat) o.g.userData.mat.opacity = 0.84 * (1 - k);
          if (k >= 1) { sahne.remove(o.g); olenler.splice(i, 1); }
        }
      }

      /* ---------------- girdi → ECS ---------------- */
      function imlecHedefi() {
        if (!H.imlec.aktif || H.imlec.dokunmatik) { imlecNokta.var = false; return null; }
        var r = H.elSahne.getBoundingClientRect();
        ndc.set(((H.imlec.x - r.left) / r.width) * 2 - 1, -((H.imlec.y - r.top) / r.height) * 2 + 1);
        raycaster.setFromCamera(ndc, H.kamera);
        if (raycaster.ray.intersectPlane(zemin, vv)) { imlecNokta.x = vv.x; imlecNokta.z = vv.z; imlecNokta.var = true; return imlecNokta; }
        return null;
      }
      function enYakinDusman(menzil) {
        var p = oyuncu.c.C_Transform, en = menzil || 1e9, bul = null;
        W.sorgu(['C_YZ', 'C_Transform', 'C_Can']).forEach(function (e) {
          if (e.c.C_Olu) return;
          var d = S.uzak(e.c.C_Transform, p); if (d < en) { en = d; bul = e; }
        });
        return bul;
      }
      function hedefBul() {
        var im = imlecHedefi(); if (im) return { x: im.x, z: im.z };
        var d = enYakinDusman(16); if (d) return { x: d.c.C_Transform.x, z: d.c.C_Transform.z };
        var p = oyuncu.c.C_Transform; return { x: p.x + p.dx * 8, z: p.z + p.dz * 8 };
      }
      A.cast = function (id) { if (!W || !oyuncu || durum.bitti || durum.geri > 0) return; S.castIste(W, oyuncu, id, hedefBul()); };
      A.etkilesim = function () { if (W && !durum.bitti) W.iste('etkilesim', {}); };

      function girdiUygula(dt) {
        var p = oyuncu.c.C_Transform, h = oyuncu.c.C_Hiz, d = oyuncu.c.C_Durum, op = oyuncu.c.C_Oyuncu;
        var ix = 0, iz = 0, t = H.tus;
        if (t.KeyA || t.ArrowLeft) ix -= 1; if (t.KeyD || t.ArrowRight) ix += 1;
        if (t.KeyW || t.ArrowUp) iz -= 1; if (t.KeyS || t.ArrowDown) iz += 1;
        if (ui.joy.aktif) { ix += ui.joy.x; iz += ui.joy.z; }
        var l = Math.sqrt(ix * ix + iz * iz); if (l > 1) { ix /= l; iz /= l; l = 1; }
        var yavas = d.islak > 0 ? 0.92 : 1;
        if (d.stun > 0 || durum.geri > 0) { h.vx = 0; h.vz = 0; }
        else { h.vx = ix * op.hiz * yavas; h.vz = iz * op.hiz * yavas; }
        return { ix: ix, iz: iz, hareket: l };
      }

      /* ---------------- ana güncelleme ---------------- */
      var vektor = new T.Vector3();
      A.guncelle = function (dt, gdt) {
        if (!W) return;
        var B = H.B, p = oyuncu.c.C_Transform;
        if (durum.geri > 0) {
          durum.geri -= gdt; var sn = Math.ceil(durum.geri);
          if (sn !== durum.geriSon && sn > 0) { durum.geriSon = sn; ui.geri(String(sn)); H.SES.geri(false); }
          if (durum.geri <= 0) { ui.geri('SAVAŞ!'); H.SES.geri(true); setTimeout(function () { ui.geri(''); }, 700); }
        }
        var gir = null;
        if (!durum.bitti) {
          gir = girdiUygula(dt);
          if (durum.geri <= 0) {
            durum.sure += dt;
            // otomatik atış: en yakın düşmana
            durum.atisT -= dt;
            if (durum.atisT <= 0) {
              var hd = enYakinDusman(11);
              if (hd && oyuncu.c.C_Durum.stun <= 0 && !(oyuncu.c.C_Atilma)) { var im = imlecHedefi(); S.castIste(W, oyuncu, 'atis', im ? { x: im.x, z: im.z } : { x: hd.c.C_Transform.x, z: hd.c.C_Transform.z }); durum.atisT = 0.42; }
              else durum.atisT = 0.1;
            }
          }
        }
        W.sistemAc('DalgaSistemi', durum.geri <= 0);
        W.sistemAc('YapayZekaSistemi', durum.geri <= 0);
        W.calistir(dt);
        // bakış yönü: nişan veya hareket
        if (!durum.bitti) {
          var imh = imlecHedefi(), hx = 0, hz = 0, atesliHedef = enYakinDusman(11);
          if (durum.kolAt > 0 && imh) { hx = imh.x - p.x; hz = imh.z - p.z; }
          else if (gir && gir.hareket > 0.1) { hx = gir.ix; hz = gir.iz; }
          else if (atesliHedef) { hx = atesliHedef.c.C_Transform.x - p.x; hz = atesliHedef.c.C_Transform.z - p.z; }
          if (hx * hx + hz * hz > 0.01) { var yn = S.norm(hx, hz); p.dx += (yn.x - p.dx) * Math.min(1, dt * 14); p.dz += (yn.z - p.dz) * Math.min(1, dt * 14); }
        }
        // karakter görseli
        var yaw = Math.atan2(-p.dx, -p.dz), gr = B.grup, fark = yaw - gr.rotation.y;
        while (fark > Math.PI) fark -= 6.2832; while (fark < -Math.PI) fark += 6.2832;
        gr.rotation.y += fark * Math.min(1, dt * 16);
        gr.position.set(p.x, 0, p.z); B.golge.position.set(p.x, 0.025, p.z);
        var hiz = Math.sqrt(oyuncu.c.C_Hiz.vx * oyuncu.c.C_Hiz.vx + oyuncu.c.C_Hiz.vz * oyuncu.c.C_Hiz.vz), atiliyor = !!oyuncu.c.C_Atilma;
        durum.faz += dt * (3.2 + hiz * 0.55) * 6.2832 * 0.45 * (hiz > 0.3 ? 1 : 0.0);
        if (!durum.bitti) {
          if (hiz > 0.3 || atiliyor) H.poz(atiliyor ? 'kayma' : 'kos', durum.faz, durum.sure, H.gdt);
          else H.poz('bekle', 0, durum.sure, H.gdt);
          if (durum.kolAt > 0) { durum.kolAt -= dt; B.shR.rotation.x = -1.55; B.elR.rotation.x = 0.25; B.shR.rotation.z = 0.05; }
          B.grup.rotation.x = 0;
          if (atiliyor) { durum.atilmaIz -= dt; if (durum.atilmaIz <= 0) { durum.atilmaIz = 0.03; vfx.izAt(p.x, 0.9, p.z, 0x55dd63, 2.2, 0.3); } }
        } else {
          var oz = H.gdt; B.grup.rotation.x = Math.min(Math.PI / 2, B.grup.rotation.x + oz * 4); B.grup.position.y = 0;
        }
        var d = oyuncu.c.C_Durum;
        B.kopuk.visible = d.kalkan > 0; if (B.kopuk.visible) { B.kopuk.scale.setScalar(1 / B.olc * (1 + Math.sin(durum.sure * 6) * 0.03)); B.kopuk.material.opacity = 0.14 + Math.min(0.2, d.kalkan / 60 * 0.2); }
        B.aura.material.opacity = d.guc > 0 ? 0.5 + Math.sin(durum.sure * 8) * 0.15 : 0; B.aura.material.color.setHex(d.guc > 0 ? 0x8fb4ff : 0xffd36a);
        // düşmanlar
        var ph = W.zaman;
        for (var id in gorsel) {
          var o = gorsel[id], e = o.e, g = o.g, tf = e.c.C_Transform;
          if (o.tip === 'toplanir') { g.position.set(tf.x, 0.7 + Math.sin(ph * 4 + +id) * 0.12, tf.z); g.rotation.y += dt * 3; var tt = e.c.C_Toplanir; g.visible = tt.omur > 3 || Math.floor(ph * 8) % 2 === 0; continue; }
          if (o.tip === 'ocak') { var u = g.userData; u.alev.scale.setScalar(3.4 + Math.sin(ph * 17) * 0.3 + Math.sin(ph * 9) * 0.2); u.alev2.scale.setScalar(1.9 + Math.sin(ph * 21) * 0.25); u.isik.intensity = 2.0 + Math.sin(ph * 13) * 0.4 + Math.sin(ph * 5) * 0.3; if (W.durum.ocakta) { if (Math.random() < dt * 14) H.parcacikPatlat(g.position.x, 2.0, g.position.z, [0x5599ff, 0xff9a3a], 1, 3); } continue; }
          if (o.tip === 'sunak') { var us = g.userData, hz = e.c.C_Etkilesim.hazir; us.kure.rotation.y += dt * 1.5; us.halka.rotation.z += dt * 2; us.kure.position.y = 2.2 + Math.sin(ph * 2) * 0.08; us.halka.position.y = us.kure.position.y; us.kure.visible = hz; us.p.material.opacity = hz ? 0.8 : 0.15; us.isik.intensity = hz ? 1.6 : 0.2; continue; }
          if (o.tip === 'sandik') { if (g.userData.flas > 0) g.userData.flas -= dt; continue; }
          if (!e.c.C_YZ) continue;
          dusmanAnim(o, e, dt, ph);
        }
        olenleriGuncelle(dt);
        vfx.guncelle(dt);
        // HUD
        hudGuncelle();
      };

      function dusmanAnim(o, e, dt, ph) {
        var g = o.g, tf = e.c.C_Transform, yz = e.c.C_YZ, u = g.userData, hv = e.c.C_Hiz, dr = e.c.C_Durum;
        g.position.x = tf.x; g.position.z = tf.z;
        var hedefYaw = Math.atan2(tf.dx, tf.dz), f = hedefYaw - g.rotation.y; while (f > Math.PI) f -= 6.2832; while (f < -Math.PI) f += 6.2832; g.rotation.y += f * Math.min(1, dt * 10);
        var sersem = dr.stun > 0, taban = u.olcek;
        if (u.flas > 0) { u.flas -= dt; }
        var fl = u.flas > 0 ? 1 : 0;
        if (u.mat) { u.mat.emissive.setHex(fl ? 0xffffff : (e.c.C_Element.tur ? V.ELEMENT[e.c.C_Element.tur].renk : 0x000000)); u.mat.emissiveIntensity = fl ? 0.9 : (e.c.C_Element.tur ? 0.35 : u.tabanEmis); if (!e.c.C_Element.tur && !fl && u.tip !== 'goblin') { u.mat.emissive.copy(u.mat.color); u.mat.emissiveIntensity = u.tabanEmis; } }
        if (u.tip === 'jole' || u.tip === 'kral') {
          var s = Math.max(0, Math.sin(ph * 5 + yz.faz)), hareketli = (yz.durum === 'kovala' && !sersem);
          var sq = hareketli ? s : 0, idle = Math.sin(ph * 2 + yz.faz) * 0.03;
          var y = 0.84 * (0.84 + 0.3 * sq + idle);
          if (yz.durum === 'vurus_hazirla') { var k = 1 - yz.t / V.DUSMAN.kral.vurusHazirlik; u.govde.scale.set(1 - k * 0.12, 0.84 + k * 0.5, 1 - k * 0.12); g.position.y = k * 1.4 * (k > 0.7 ? 1 : 0.4); }
          else { u.govde.scale.set(1 - 0.12 * sq + 0.05 * (1 - sq) * (hareketli ? 1 : 0), 0.84 + 0.3 * sq + idle, 1 - 0.12 * sq); g.position.y = sq * 0.55 * (u.tip === 'kral' ? 0.5 : 1); }
          u.govde.position.y = 0.84 * u.govde.scale.y;
          u.yuz.position.y = u.govde.position.y + 0.06;
          if (u.cekler) u.cekler.children.forEach(function (c, i) { c.userData.a += dt * 1.2; c.position.set(Math.cos(c.userData.a) * 0.55, 0.8 + Math.sin(ph * 2 + i) * 0.22, Math.sin(c.userData.a) * 0.55); });
        } else if (u.tip === 'goblin') {
          var vv2 = Math.sqrt(hv.vx * hv.vx + hv.vz * hv.vz), sw = Math.sin(ph * 11 + yz.faz) * Math.min(1, vv2 / 3) * 0.9;
          u.bS.rotation.x = sw; u.bD.rotation.x = -sw; u.kS.rotation.x = -sw * 0.8;
          u.govde.position.y = 0.7 + Math.abs(Math.cos(ph * 11 + yz.faz)) * 0.06 * Math.min(1, vv2 / 3);
          if (yz.durum === 'hazirla') { var k2 = 1 - yz.t / V.DUSMAN.goblin.hazirlik; u.kD.rotation.x = -0.5 - k2 * 2.2; u.govde.rotation.x = -k2 * 0.25; }
          else { u.kD.rotation.x = sw * 0.8 - 0.2 + (yz.bekleme > V.DUSMAN.goblin.bekle - 0.2 ? 1.4 : 0); u.govde.rotation.x = 0.08; }
        }
        if (sersem) { g.rotation.z = Math.sin(ph * 20) * 0.1; } else g.rotation.z *= 0.8;
      }

      function hudGuncelle() {
        var c = oyuncu.c, yet = c.C_Yetenek.cd, hp = c.C_Can, et = c.C_Ether, st = c.C_Stamina, d = c.C_Durum;
        var cd = {};
        V.TUS.arena.sira.forEach(function (id) {
          var y = V.YETENEK[id], kalan = yet[id] || 0, yetersiz = (y.kaynak === 'ether' && et.v < y.maliyet) || (y.kaynak === 'stamina' && st.v < y.maliyet);
          cd[id] = { oran: y.cd ? Math.min(1, kalan / y.cd) : 0, yetersiz: yetersiz };
        });
        var boss = null;
        W.sorgu(['C_YZ']).forEach(function (e) { if (!e.c.C_Olu && V.DUSMAN[e.c.C_YZ.tip].boss) boss = { ad: V.DUSMAN[e.c.C_YZ.tip].ad, oran: e.c.C_Can.hp / e.c.C_Can.max }; });
        var ds = W.durum.dalga, canli = W.sorgu(['C_YZ']).filter(function (e) { return !e.c.C_Olu; }).length + (ds ? ds.kuyruk.length : 0);
        var et2 = W.durum.etkilesim;
        ui.hud.guncelle({
          can: hp.hp, canMax: hp.max, kalkan: d.kalkan, ether: et.v, etherMax: et.max, stamina: st.v, staminaMax: st.max,
          skor: Math.floor(W.durum.skor), kombo: W.durum.kombo || 0, carpan: Math.min(3, 1 + Math.floor((W.durum.kombo || 0) / 5) * 0.25), cekirdek: durum.oldurme, cekEtiket: 'yenilen',
          ust: { baslik: ds && ds.aktif ? 'Dalga ' + ds.no + ' · ' + canli + ' düşman' : (ds && ds.no ? 'Dalga ' + ds.no + ' temizlendi' : 'Hazırlan'), oran: 0 },
          boss: boss, cd: cd, guclar: [{ id: 'guc', ad: 'Geek Gücü', renk: '#8fb4ff', oran: d.guc / 20 }],
          ipucu: et2 ? (et2.tip === 'sunak' ? 'Geek Sunağı' : '') : '', ipucuTus: 'E'
        });
        var az = hp.hp / hp.max < 0.3 && !durum.bitti; if (az !== durum.azCan) { durum.azCan = az; ui.azCan(az); }
      }

      A.kamera = function (dt) {
        var k = H.kamera, dikey = innerWidth / innerHeight < 0.9, p = oyuncu ? oyuncu.c.C_Transform : { x: 0, z: 0 };
        var yuk = dikey ? 21 : 15.5, geri = dikey ? 12.5 : 10.5, boss = W && W.sorgu(['C_YZ']).some(function (e) { return !e.c.C_Olu && e.c.C_YZ.tip === 'kral'; });
        if (boss) { yuk += 2.5; geri += 1.5; }
        var cx = p.x * 0.85, cz = p.z * 0.85, sars = H.sarsinti(dt);
        k.fov += ((dikey ? 62 : 48) - k.fov) * Math.min(1, dt * 3); k.updateProjectionMatrix();
        k.position.x += (cx + (Math.random() - 0.5) * sars - k.position.x) * Math.min(1, dt * 7);
        k.position.y += (yuk + (Math.random() - 0.5) * sars - k.position.y) * Math.min(1, dt * 3);
        k.position.z += (cz + geri - k.position.z) * Math.min(1, dt * 7);
        k.lookAt(p.x * 0.9, 0.6, p.z * 0.9 - 0.5);
        k.rotation.z = 0;
        // ay ışığı oyuncuyu izler (gölge kalitesi)
        if (isik.ay) { isik.ay.position.set(p.x - 10, 24, p.z + 8); isik.ay.target.position.set(p.x, 0, p.z); }
      };
      A.ozet = function () {
        var skor = Math.floor(W.durum.skor), ds = W.durum.dalga;
        return { skor: skor, sure: Math.floor(durum.sure), dalga: ds ? ds.no : 0, oldurme: durum.oldurme, enKombo: durum.enKombo };
      };
      A.durum = function () { return durum; };
      A.dunya = function () { return W; };
      A.baslat = baslat;
      A.temizle = function () { temizleDunya(); W = null; oyuncu = null; ui.azCan(false); };
      A.sahneKur = function () { if (!A.hazir) sahneKur(); };
      A.bitir = function () { durum.bitti = true; };
      return A;
    }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = NS;
})(typeof window !== 'undefined' ? window : globalThis);
