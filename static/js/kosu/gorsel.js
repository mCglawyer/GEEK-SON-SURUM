/* Geek Oyun · efekt katmanı (iki mod da kullanır): mermi, yağmur alanı, şimşek, patlama, uyarı halkaları, hasar sayıları.
   ECS gözlemcileriyle beslenir; kendi nesnelerini verilen sahnede yönetir. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var V = NS.veri;

  NS.gorsel = {
    kur: function (H) {
      var T = H.T, sahne = null, W = null, kapsayici = H.kok;
      var obj = {};              // varlik id → { g, tip }
      var efektler = [];         // süreli efektler: { g, t, omur, fn }
      var izler = [], sayilar = [];
      var geoKure = new T.SphereGeometry(1, 14, 10), geoHalka = new T.RingGeometry(0.86, 1, 56), geoDisk = new T.CircleGeometry(1, 48);
      geoHalka.rotateX(-Math.PI / 2); geoDisk.rotateX(-Math.PI / 2);
      var matCache = {};
      function basit(renk, opak, ek) {
        var a = renk + '_' + opak + '_' + (ek ? 1 : 0);
        if (!matCache[a]) matCache[a] = new T.MeshBasicMaterial({ color: renk, transparent: true, opacity: opak, depthWrite: false, blending: ek ? T.AdditiveBlending : T.NormalBlending, side: T.DoubleSide, fog: false });
        return matCache[a].clone();
      }
      function renkOf(el) { return el && V.ELEMENT[el] ? V.ELEMENT[el].renk : 0xffffff; }

      /* ---- sayaç/yüzen yazılar (DOM) ---- */
      var katman = document.createElement('div'); katman.className = 'go-sayilar'; kapsayici.appendChild(katman);
      function sayiAt(x, y, z, metin, sinif) {
        var s = sayilar.find(function (q) { return !q.aktif; });
        if (!s) { if (sayilar.length > 28) return; s = { d: document.createElement('div'), aktif: false }; katman.appendChild(s.d); sayilar.push(s); }
        s.aktif = true; s.t = 0; s.x = x + (Math.random() - 0.5) * 0.5; s.y = y; s.z = z; s.d.className = 'go-sayi ' + (sinif || ''); s.d.textContent = metin; s.d.style.display = 'block';
      }
      function sayilariGuncelle(dt) {
        sayilar.forEach(function (s) {
          if (!s.aktif) return;
          s.t += dt; if (s.t > 0.95) { s.aktif = false; s.d.style.display = 'none'; return; }
          var p = H.projeEt(s.x, s.y + s.t * 1.4, s.z);
          if (!p) { s.d.style.display = 'none'; return; }
          s.d.style.display = 'block'; s.d.style.transform = 'translate(' + p.x.toFixed(0) + 'px,' + p.y.toFixed(0) + 'px) translate(-50%,-50%) scale(' + (1 + Math.max(0, 0.25 - s.t) * 2).toFixed(2) + ')';
          s.d.style.opacity = Math.min(1, (0.95 - s.t) * 3).toFixed(2);
        });
      }

      /* ---- iz sprite'ları ---- */
      function izAt(x, y, z, renk, olcek, omur) {
        var s = izler.find(function (q) { return !q.g.visible; });
        if (!s) { if (izler.length > 90) return; s = { g: H.parlama(renk, 1, 0.8), omur: 0, t: 0, o: 1 }; izler.push(s); sahne.add(s.g); }
        else if (s.g.parent !== sahne) sahne.add(s.g);
        s.g.visible = true; s.g.material.color.setHex(renk); s.g.position.set(x, y, z); s.omur = omur || 0.35; s.t = 0; s.o = olcek || 1; s.g.scale.setScalar(s.o);
      }
      function izlerGuncelle(dt) {
        izler.forEach(function (s) {
          if (!s.g.visible) return;
          s.t += dt; if (s.t >= s.omur) { s.g.visible = false; return; }
          var k = 1 - s.t / s.omur; s.g.scale.setScalar(s.o * (0.4 + k * 0.6)); s.g.material.opacity = 0.8 * k;
        });
      }
      function efektEkle(g, omur, fn) { sahne.add(g); efektler.push({ g: g, t: 0, omur: omur, fn: fn }); return g; }

      /* ---- gözlemciler ---- */
      function mermiGorseli(m) {
        var g = new T.Group(), renk = m.element ? renkOf(m.element) : 0xd9a65a;
        if (m.tur === 'top') {
          var ic = new T.Mesh(geoKure, basit(0xfff1c2, 1, true)); ic.scale.setScalar(0.2); g.add(ic);
          var d = new T.Mesh(geoKure, basit(renk, 0.9, true)); d.scale.setScalar(0.38); g.add(d);
          g.add(H.parlama(renk, 2.6, 0.9));
        } else {
          var bardak = new T.Mesh(new T.CylinderGeometry(0.17, 0.13, 0.3, 12), new T.MeshStandardMaterial({ color: 0xffffff, roughness: 0.5 }));
          g.add(bardak); var kapak = new T.Mesh(new T.CylinderGeometry(0.18, 0.18, 0.05, 12), new T.MeshStandardMaterial({ color: 0x0b0f2e })); kapak.position.y = 0.17; g.add(kapak);
          g.add(H.parlama(0xffd36a, 1.0, 0.5));
        }
        return g;
      }
      function alanGorseli(a) {
        var g = new T.Group(), r = a.r;
        var disk = new T.Mesh(geoDisk, basit(0x2f9cff, 0.2, false)); disk.scale.setScalar(r); disk.position.y = 0.04; g.add(disk);
        var hal = new T.Mesh(geoHalka, basit(0x9fdcff, 0.85, true)); hal.scale.setScalar(r); hal.position.y = 0.06; g.add(hal);
        var n = 70, pos = new Float32Array(n * 6), geo = new T.BufferGeometry(); geo.setAttribute('position', new T.BufferAttribute(pos, 3));
        var cizgi = new T.LineSegments(geo, new T.LineBasicMaterial({ color: 0xcfe9ff, transparent: true, opacity: 0.7, depthWrite: false })); cizgi.frustumCulled = false; g.add(cizgi);
        var bulut = H.parlama(0x7a8fb0, r * 2.6, 0.6); bulut.position.y = 6.2; g.add(bulut);
        g.userData = { n: n, hx: [], hy: [], hz: [], r: r, cizgi: cizgi, disk: disk, hal: hal };
        for (var i = 0; i < n; i++) { var a2 = Math.random() * 6.283, rr = Math.sqrt(Math.random()) * r; g.userData.hx.push(Math.cos(a2) * rr); g.userData.hz.push(Math.sin(a2) * rr); g.userData.hy.push(Math.random() * 6); }
        return g;
      }

      function bagla(dunya, hedefSahne) {
        W = dunya; sahne = hedefSahne;
        W.on('varlik_dogdu', function (e) {
          if (e.c.C_Mermi) { var g = mermiGorseli(e.c.C_Mermi); sahne.add(g); obj[e.id] = { g: g, tip: 'mermi' }; }
          else if (e.c.C_Alan && e.c.C_Alan.tur === 'firtina') { var z = alanGorseli(e.c.C_Alan); sahne.add(z); obj[e.id] = { g: z, tip: 'alan' }; }
        });
        W.on('varlik_oldu', function (e) { var o = obj[e.id]; if (o) { sahne.remove(o.g); delete obj[e.id]; } });
        W.on('cast', function (c) {
          if (c.id === 'top' || c.id === 'atis') { H.SES.top && H.SES.top(); }
          else if (c.id === 'patlama') { /* patlama olayında */ }
          else if (c.id === 'dash') { H.SES.dash && H.SES.dash(); }
          else if (c.id === 'kalkan') { H.SES.kalkan && H.SES.kalkan(); }
        });
        W.on('mermi_vurdu', function (e) {
          var r = renkOf(e.element) || 0xffffff;
          H.parcacikPatlat(e.x, 1.1, e.z, [r, 0xffffff, 0xffd36a], 10, 6);
          izAt(e.x, 1.1, e.z, r, 2.6, 0.25); H.SES.vurus && H.SES.vurus();
        });
        W.on('mermi_sondu', function (e) { if (e.tur === 'top') izAt(e.x, 1.1, e.z, 0xff9a55, 1.8, 0.25); });
        W.on('simsek', function (s) { simsekCiz(s.noktalar); });
        W.on('patlama', function (e) { patlamaCiz(e); });
        W.on('tepkime_alani', function (e) { halkaCiz(e.x, e.z, e.r, 0xc796ff, 0.45); H.parcacikPatlat(e.x, 1, e.z, [0xc796ff, 0xffffff, 0xff9a55], 16, 8); });
        W.on('alan_bitti', function () {});
        W.on('yere_vurus_hazirlik', function (e) { uyariHalka(e.varlik, e.r, e.sure, true); });
        W.on('saldiri_hazirlik', function (e) { uyariHalka(e.varlik, 1.6, e.sure, false); });
        W.on('yere_vurus', function (e) { halkaCiz(e.x, e.z, e.r, 0xff6a5a, 0.5); H.parcacikPatlat(e.x, 0.4, e.z, [0xff6a5a, 0xffffff, 0xbda573], 30, 10); H.sars(0.7); H.SES.carpma && H.SES.carpma(); });
        W.on('hasar_uygulandi', function (e) {
          var p = e.hedef.c.C_Transform, oyuncu = !!e.hedef.c.C_Oyuncu;
          if (e.miktar > 0) sayiAt(p.x, oyuncu ? 2.2 : 1.8, p.z, String(Math.round(e.miktar)), oyuncu ? 'kotu' : (e.element || ''));
          else if (e.emilen > 0) sayiAt(p.x, 2.2, p.z, 'Emildi', 'iyi');
          if (e.tepkime) { sayiAt(p.x, 2.5, p.z, e.tepkime.ad + '!', 'tepkime'); if (H.ui) H.ui.gunluk(e.tepkime.ad + ' tepkimesi', 'tepkime'); }
        });
        W.on('blok', function (e) { var p = e.hedef.c.C_Transform; sayiAt(p.x, 2.2, p.z, 'Kaçtın', 'iyi'); });
      }

      function halkaCiz(x, z, r, renk, omur) {
        var h = new T.Mesh(geoHalka, basit(renk, 0.9, true)); h.position.set(x, 0.1, z);
        efektEkle(h, omur || 0.45, function (k) { h.scale.setScalar(Math.max(0.05, r * (0.15 + k * 0.85))); h.material.opacity = 0.9 * (1 - k); });
      }
      function patlamaCiz(e) {
        var renk = renkOf(e.element) || 0xff7a2a;
        halkaCiz(e.x, e.z, e.r, renk, 0.5);
        var yarim = new T.Mesh(geoKure, basit(renk, 0.45, true)); yarim.position.set(e.x, 0.3, e.z);
        efektEkle(yarim, 0.45, function (k) { yarim.scale.setScalar(Math.max(0.05, e.r * (0.2 + k * 0.8))); yarim.material.opacity = 0.5 * (1 - k); });
        var p = H.parlama(0xffe0a0, e.r * 3.2, 1); p.position.set(e.x, 1.4, e.z);
        efektEkle(p, 0.4, function (k) { p.material.opacity = 1 - k; p.scale.setScalar(e.r * (2.4 + k * 1.2)); });
        H.parcacikPatlat(e.x, 0.5, e.z, [renk, 0xffd36a, 0xffffff, 0x5b3317], 44, 14);
        H.sars(1.0); H.flas('#ffd9a0'); H.titre([30, 30, 60]); H.SES.patlama && H.SES.patlama();
      }
      function uyariHalka(varlik, r, sure, buyuk) {
        var p = varlik.c.C_Transform, g = new T.Group();
        var disk = new T.Mesh(geoDisk, basit(0xff4a3a, 0.25, false)), halka = new T.Mesh(geoHalka, basit(0xff8a7a, 0.9, true));
        disk.position.y = 0.05; halka.position.y = 0.06; halka.scale.setScalar(r); g.add(disk); g.add(halka); g.position.set(p.x, 0, p.z);
        efektEkle(g, sure, function (k) {
          g.position.set(varlik.c.C_Transform.x, 0, varlik.c.C_Transform.z);
          disk.scale.setScalar(Math.max(0.01, r * k)); disk.material.opacity = 0.18 + 0.3 * k;
        });
      }
      function simsekCiz(noktalar) {
        var renk = renkOf('electro');
        for (var i = 0; i < noktalar.length - 1; i++) {
          var a = noktalar[i], b = noktalar[i + 1], parca = Math.max(4, Math.round(Math.hypot(b.x - a.x, b.z - a.z) / 1.1));
          var pts = [];
          for (var k = 0; k <= parca; k++) {
            var t = k / parca, jx = (k === 0 || k === parca) ? 0 : (Math.random() - 0.5) * 0.9, jy = (k === 0 || k === parca) ? 0 : (Math.random() - 0.5) * 0.7;
            pts.push(new T.Vector3(a.x + (b.x - a.x) * t + jx, a.y + (b.y - a.y) * t + jy, a.z + (b.z - a.z) * t + jx));
          }
          var geo = new T.BufferGeometry().setFromPoints(pts);
          var cizgi = new T.Line(geo, new T.LineBasicMaterial({ color: 0xf1e3ff, transparent: true, opacity: 1, blending: T.AdditiveBlending, depthWrite: false, fog: false }));
          cizgi.frustumCulled = false;
          var grp = new T.Group(); grp.add(cizgi);
          pts.forEach(function (p, idx) { if (idx % 2 === 0) { var sp = H.parlama(renk, 1.5, 0.8); sp.position.copy(p); grp.add(sp); } });
          (function (grp, cizgi) { efektEkle(grp, 0.22, function (k) { cizgi.material.opacity = 1 - k; grp.children.forEach(function (c) { if (c.isSprite) c.material.opacity = 0.8 * (1 - k); }); }); })(grp, cizgi);
        }
        noktalar.slice(1).forEach(function (p) { H.parcacikPatlat(p.x, 1.0, p.z, [renk, 0xffffff], 12, 8); izAt(p.x, 1.0, p.z, renk, 3.2, 0.3); });
        H.flas('#e5d0ff'); H.sars(0.4); H.SES.simsekAt && H.SES.simsekAt();
      }

      function guncelle(dt) {
        if (!W) return;
        // mermi + alan senkronu
        for (var id in obj) {
          var o = obj[id], e = W.al(+id);
          if (!e) continue;
          if (o.tip === 'mermi') {
            var p = e.c.C_Transform, m = e.c.C_Mermi;
            o.g.position.set(p.x, p.y, p.z); o.g.rotation.y += dt * 9;
            if (m.tur === 'top') izAt(p.x - p.dx * 0.3, p.y, p.z - p.dz * 0.3, renkOf(m.element), 1.5, 0.3);
          } else if (o.tip === 'alan') {
            var a = e.c.C_Alan, u = o.g.userData, pa = e.c.C_Transform;
            o.g.position.set(pa.x, 0, pa.z);
            var solma = Math.min(1, a.sure / 0.6), pos = u.cizgi.geometry.attributes.position.array;
            for (var i = 0; i < u.n; i++) {
              u.hy[i] -= 22 * dt; if (u.hy[i] < 0) u.hy[i] += 6;
              var q = i * 6; pos[q] = u.hx[i]; pos[q + 1] = u.hy[i]; pos[q + 2] = u.hz[i]; pos[q + 3] = u.hx[i]; pos[q + 4] = u.hy[i] + 0.6; pos[q + 5] = u.hz[i];
            }
            u.cizgi.geometry.attributes.position.needsUpdate = true; u.cizgi.material.opacity = 0.7 * solma; u.disk.material.opacity = 0.2 * solma; u.hal.material.opacity = 0.85 * solma;
            u.hal.scale.setScalar(u.r * (1 + Math.sin(W.zaman * 6) * 0.015));
          }
        }
        for (var j = efektler.length - 1; j >= 0; j--) {
          var f = efektler[j]; f.t += dt;
          var k = Math.min(1, f.t / f.omur); f.fn(k);
          if (f.t >= f.omur) { sahne.remove(f.g); f.g.traverse(function (c) { if (c.material && c.material.dispose && !c.isSprite) c.material.dispose(); }); efektler.splice(j, 1); }
        }
        izlerGuncelle(dt); sayilariGuncelle(dt);
      }
      function temizle() {
        for (var id in obj) { if (obj[id].g.parent) obj[id].g.parent.remove(obj[id].g); }
        obj = {};
        efektler.forEach(function (f) { if (f.g.parent) f.g.parent.remove(f.g); }); efektler = [];
        izler.forEach(function (s) { s.g.visible = false; });
        sayilar.forEach(function (s) { s.aktif = false; s.d.style.display = 'none'; });
        W = null;
      }
      function sahneDegistir(yeni) { izler.forEach(function (s) { sahne.remove(s.g); }); sahne = yeni; }
      return { bagla: bagla, guncelle: guncelle, temizle: temizle, sayiAt: sayiAt, halkaCiz: halkaCiz, izAt: izAt, sahneDegistir: sahneDegistir };
    }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = NS;
})(typeof window !== 'undefined' ? window : globalThis);
