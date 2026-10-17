/* Geek Oyun · oyun sistemleri (saf mantık, çizimden bağımsız; Node'da test edilir).
   Özellikler (Reia'daki gibi klasörlenmiş): durum · istatistik (can/ether/dayanıklılık) · hasar · yetenek · mermi/alan · yapay zeka · dalga · toplanır · etkileşim · ölüm.
   Hepsi aynı ECS dünyasında çalışır; Koşu ve Arena modları farklı sistemleri açarak aynı kuralları paylaşır. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var V = NS.veri;
  var sin = Math.sin, sqrt = Math.sqrt, max = Math.max, min = Math.min;

  /* ======================= yardımcılar ======================= */
  function tf(e) { return e.c.C_Transform; }
  function uzak(a, b) { var dx = a.x - b.x, dz = a.z - b.z; return sqrt(dx * dx + dz * dz); }
  function norm(x, z, yedek) { var l = sqrt(x * x + z * z); if (l < 1e-6) return yedek || { x: 0, z: -1 }; return { x: x / l, z: z / l }; }
  function dusmanMi(w, kaynakTakim, e) {
    if (e.olu || e.c.C_Olu || !e.c.C_Can || !e.c.C_Takim) return false;
    var t = e.c.C_Takim.t;
    if (kaynakTakim === 'oyuncu') return t === 'dusman' || t === 'engel';
    if (kaynakTakim === 'dusman') return t === 'oyuncu';
    return false;
  }
  function hedefler(w, takim) {
    return w.sorgu(['C_Transform', 'C_Cisim', 'C_Can', 'C_Takim']).filter(function (e) { return dusmanMi(w, takim, e); });
  }
  function gucCarpan(e) { return (e && e.c.C_Durum && e.c.C_Durum.guc > 0) ? 1.5 : 1; }
  function oyuncular(w) { return w.sorgu(['C_Oyuncu', 'C_Transform', 'C_Can']).filter(function (e) { return !e.c.C_Olu; }); }

  /* ======================= prefablar ======================= */
  function prefablariKur(w) {
    w.prefab('oyuncu', function (w, a) {
      var o = a.ozellik || {};
      return w.yarat({
        C_Transform: { x: a.x || 0, y: 0, z: a.z || 0, dx: 0, dz: -1 },
        C_Hiz: { vx: 0, vz: 0 }, C_Cisim: { r: 0.5 }, C_Takim: { t: 'oyuncu' },
        C_Can: { hp: 100, max: 100, regen: o.canRegen || 0, bekle: 0 },
        C_Ether: { v: o.ether === undefined ? 100 : o.ether, max: 100, regen: o.etherRegen === undefined ? 3.5 : o.etherRegen },
        C_Stamina: { v: 100, max: 100, regen: 22, bekle: 0, gecikme: 0.7 },
        C_Durum: { stun: 0, dokunulmaz: 0, yanik: 0, yanikHasar: 0, yanikT: 0, islak: 0, kalkan: 0, kalkanT: 0, guc: 0 },
        C_Element: { tur: null, t: 0 },
        C_Yetenek: { cd: {} },
        C_Oyuncu: { yara: o.yara === undefined ? 0.55 : o.yara, hiz: o.hiz || 6.3 },
        C_Sinir: {}
      }, 'oyuncu');
    });
    w.prefab('mermi', function (w, a) {
      return w.yarat({
        C_Transform: { x: a.x, y: a.y === undefined ? 1.0 : a.y, z: a.z, dx: a.dx, dz: a.dz },
        C_Mermi: { sahip: a.sahip, takim: a.takim, hasar: a.hasar, element: a.element || null, omur: a.omur || 1, hiz: a.hiz, r: a.r || 0.4, delici: !!a.delici, vurdu: {}, tur: a.tur || 'top', px: a.x, pz: a.z }
      }, 'mermi');
    });
    w.prefab('alan', function (w, a) {
      return w.yarat({
        C_Transform: { x: a.x, y: 0, z: a.z, dx: 0, dz: 1 },
        C_Alan: { sahip: a.sahip, takim: a.takim, r: a.r, sure: a.sure, ilkSure: a.sure, tick: a.tick, tickT: 0.05, hasar: a.hasar, element: a.element, tur: a.tur || 'firtina' }
      }, 'alan');
    });
    w.prefab('dusman', function (w, a) {
      var d = V.DUSMAN[a.tip], olc = a.olcek || 1, hp = Math.round(d.can * (1 + 0.1 * ((a.dalga || 1) - 1)));
      return w.yarat({
        C_Transform: { x: a.x, y: 0, z: a.z, dx: 0, dz: 1 },
        C_Hiz: { vx: 0, vz: 0 }, C_Cisim: { r: d.r * olc }, C_Takim: { t: 'dusman' },
        C_Can: { hp: hp, max: hp, regen: 0, bekle: 0 },
        C_Durum: { stun: 0, dokunulmaz: 0, yanik: 0, yanikHasar: 0, yanikT: 0, islak: 0, kalkan: 0, kalkanT: 0, guc: 0 },
        C_Element: { tur: null, t: 0 },
        C_YZ: { tip: a.tip, durum: 'bekle', bekleme: 0.4 + w.rastgele() * 0.4, t: 0, faz: w.rastgele() * 6.28, vurusT: d.boss ? 3.5 : 0, esik: [false, false] },
        C_Puan: { deger: d.puan }, C_Sinir: {}
      }, 'dusman_' + a.tip);
    });
    w.prefab('toplanir', function (w, a) {
      return w.yarat({
        C_Transform: { x: a.x, y: 0.7, z: a.z, dx: 0, dz: 1 },
        C_Toplanir: { tur: a.tur, deger: a.deger, omur: a.omur || 14 }
      }, 'toplanir_' + a.tur);
    });
    w.prefab('engel', function (w, a) {       // Koşu: engeller de ECS varlığıdır, böylece yetenekler onları kırabilir
      return w.yarat({
        C_Transform: { x: a.x, y: 0, z: a.z, dx: 0, dz: 1 },
        C_Cisim: { r: a.r || 1.0 }, C_Takim: { t: 'engel' }, C_Can: { hp: a.can || 20, max: a.can || 20, regen: 0, bekle: 0 },
        C_Element: { tur: null, t: 0 }, C_Puan: { deger: a.puan || 25 }, C_Engel: { ref: a.ref || null }
      }, 'engel');
    });
    w.prefab('prop', function (w, a) {
      var c = { C_Transform: { x: a.x, y: 0, z: a.z, dx: 0, dz: 1 }, C_Cisim: { r: a.r || 0.8 }, C_Prop: { tip: a.tip } };
      if (a.tip === 'sandik') { c.C_Takim = { t: 'engel' }; c.C_Can = { hp: 30, max: 30, regen: 0, bekle: 0 }; c.C_Element = { tur: null, t: 0 }; c.C_Puan = { deger: 5 }; }
      if (a.tip === 'ocak') c.C_Etkilesim = { tip: 'ocak', menzil: 3.4, hazir: true };
      if (a.tip === 'sunak') c.C_Etkilesim = { tip: 'sunak', menzil: 2.4, hazir: true };
      return w.yarat(c, 'prop_' + a.tip);
    });
  }

  /* ======================= hasar ======================= */
  function hasarIste(w, hedef, miktar, s) {
    w.iste('hasar', { hedef: hedef, miktar: miktar, s: s || {} });
  }
  function itmeUygula(hedef, ix, iz, g) {
    if (!hedef.c.C_Hiz) return;
    var d = hedef.c.C_YZ && V.DUSMAN[hedef.c.C_YZ.tip].boss ? 0.15 : 1;
    var it = hedef.c.C_Itme || (hedef.c.C_Itme = { x: 0, z: 0 });
    it.x += ix * g * d; it.z += iz * g * d;
  }
  function tepkimeBul(a, b) {
    if (!a || !b || a === b) return null;
    var k = [a, b].sort().join('+');
    return V.TEPKIME[k] || null;
  }

  function HasarSistemi(w) {
    var guvenlik = 0;
    while (guvenlik++ < 80) {
      var liste = w.tuket('hasar');
      if (!liste.length) break;
      for (var i = 0; i < liste.length; i++) hasarUygula(w, liste[i]);
    }
  }
  function hasarUygula(w, r) {
    var t = r.hedef, s = r.s, can = t && t.c.C_Can, d = t && t.c.C_Durum;
    if (!t || t.olu || !can || t.c.C_Olu) return;
    var miktar = r.miktar * (s.kaynak ? gucCarpan(s.kaynak) : 1);
    if (d && d.dokunulmaz > 0 && !s.yoksay) { w.emit('blok', { hedef: t, kaynak: s.kaynak }); return; }
    var tepkime = null;
    if (s.element && t.c.C_Element) {
      var au = t.c.C_Element;
      tepkime = tepkimeBul(au.tur, s.element);
      if (tepkime) {
        miktar *= tepkime.carpan; au.tur = null; au.t = 0;
        if (tepkime.sersem && d) d.stun = max(d.stun, tepkime.sersem);
      } else { au.tur = s.element; au.t = s.element === 'hydro' ? 8 : 6; }
      if (s.element === 'pyro' && !tepkime && d) { d.yanik = 3; d.yanikHasar = 5; }
      if (s.element === 'hydro' && d) d.islak = 6;
    }
    var emilen = 0;
    if (d && d.kalkan > 0) {
      emilen = min(d.kalkan, miktar); d.kalkan -= emilen; miktar -= emilen;
      if (d.kalkan <= 0) { d.kalkan = 0; d.kalkanT = 0; w.emit('kalkan_kirildi', { hedef: t }); }
    }
    miktar = Math.round(miktar * 10) / 10;
    can.hp = max(0, can.hp - miktar);
    can.bekle = 3;
    if (t.c.C_Oyuncu && miktar > 0 && d && !s.yoksay) d.dokunulmaz = max(d.dokunulmaz, t.c.C_Oyuncu.yara);
    if (s.itme) itmeUygula(t, s.itme.x, s.itme.z, s.itme.g || 6);
    w.emit('hasar_uygulandi', { hedef: t, kaynak: s.kaynak || null, miktar: miktar, emilen: emilen, element: s.element || null, tepkime: tepkime, tur: s.tur || null });
    if (tepkime && tepkime.alan) {
      var p = tf(t), a = tepkime.alan;
      w.emit('tepkime_alani', { x: p.x, z: p.z, r: a.r, tepkime: tepkime });
      hedefler(w, s.kaynak && s.kaynak.c.C_Takim ? s.kaynak.c.C_Takim.t : 'oyuncu').forEach(function (h) {
        if (h === t) return;
        var hp = tf(h), dd = uzak(hp, p);
        if (dd <= a.r + h.c.C_Cisim.r) {
          var y = norm(hp.x - p.x, hp.z - p.z);
          hasarIste(w, h, a.hasar, { kaynak: s.kaynak, itme: { x: y.x, z: y.z, g: a.itme } });
        }
      });
    }
    if (can.hp <= 0 && !t.c.C_Olu) { w.ekle(t, 'C_Olu', { isl: false, katil: s.kaynak || null }); }
  }

  /* ======================= durum / yenileme ======================= */
  function DurumSistemi(w, dt) {
    w.sorgu(['C_Durum']).forEach(function (e) {
      if (e.c.C_Olu) return;
      var d = e.c.C_Durum;
      if (d.stun > 0) d.stun = max(0, d.stun - dt);
      if (d.dokunulmaz > 0) d.dokunulmaz = max(0, d.dokunulmaz - dt);
      if (d.islak > 0) d.islak = max(0, d.islak - dt);
      if (d.guc > 0) d.guc = max(0, d.guc - dt);
      if (d.kalkanT > 0) { d.kalkanT -= dt; if (d.kalkanT <= 0 && d.kalkan > 0) { d.kalkan = 0; w.emit('kalkan_bitti', { hedef: e }); } }
      if (d.yanik > 0) {
        d.yanik = max(0, d.yanik - dt); d.yanikT += dt;
        if (d.yanikT >= 0.5) { d.yanikT -= 0.5; hasarIste(w, e, d.yanikHasar * 0.5, { yoksay: true, tur: 'yanik' }); }
      }
      if (e.c.C_Element && e.c.C_Element.tur) { e.c.C_Element.t -= dt; if (e.c.C_Element.t <= 0) e.c.C_Element.tur = null; }
    });
  }
  function YenilemeSistemi(w, dt) {
    w.sorgu(['C_Can']).forEach(function (e) {
      if (e.c.C_Olu) return;
      var c = e.c.C_Can;
      if (c.bekle > 0) c.bekle -= dt; else if (c.regen > 0 && c.hp < c.max) c.hp = min(c.max, c.hp + c.regen * dt);
    });
    w.sorgu(['C_Ether']).forEach(function (e) { var s = e.c.C_Ether; if (!e.c.C_Olu && s.v < s.max) s.v = min(s.max, s.v + s.regen * dt); });
    w.sorgu(['C_Stamina']).forEach(function (e) {
      var s = e.c.C_Stamina; if (e.c.C_Olu) return;
      if (s.bekle > 0) s.bekle -= dt; else if (s.v < s.max) s.v = min(s.max, s.v + s.regen * dt);
    });
    w.sorgu(['C_Yetenek']).forEach(function (e) {
      var cd = e.c.C_Yetenek.cd;
      for (var k in cd) if (cd[k] > 0) cd[k] = max(0, cd[k] - dt);
    });
  }

  /* ======================= yetenekler ======================= */
  function castIste(w, kaynak, id, hedefNokta, yon) {
    w.iste('cast', { kaynak: kaynak, id: id, hedef: hedefNokta || null, yon: yon || null });
  }
  function castDurumu(w, kaynak, id) {
    var y = V.yetenek(id, w.mod);
    if (!y || y.modlar.indexOf(w.mod) < 0) return { ok: false, neden: 'mod' };
    if (!kaynak || kaynak.olu || kaynak.c.C_Olu) return { ok: false, neden: 'olu' };
    var d = kaynak.c.C_Durum;
    if (d && d.stun > 0) return { ok: false, neden: 'sersem' };
    var yc = kaynak.c.C_Yetenek;
    if (yc && yc.cd[id] > 0) return { ok: false, neden: 'bekleme', kalan: yc.cd[id] };
    if (y.kaynak === 'ether' && (!kaynak.c.C_Ether || kaynak.c.C_Ether.v < y.maliyet)) return { ok: false, neden: 'ether' };
    if (y.kaynak === 'stamina' && (!kaynak.c.C_Stamina || kaynak.c.C_Stamina.v < y.maliyet)) return { ok: false, neden: 'dayaniklilik' };
    return { ok: true, y: y };
  }

  function CastSistemi(w) {
    var liste = w.tuket('cast');
    for (var i = 0; i < liste.length; i++) {
      var r = liste[i], k = r.kaynak, durum = castDurumu(w, k, r.id);
      if (!durum.ok) { w.emit('cast_reddedildi', { kaynak: k, id: r.id, neden: durum.neden }); continue; }
      var y = durum.y, p = tf(k);
      if (y.kaynak === 'ether') k.c.C_Ether.v -= y.maliyet;
      else if (y.kaynak === 'stamina') { k.c.C_Stamina.v -= y.maliyet; k.c.C_Stamina.bekle = k.c.C_Stamina.gecikme; }
      if (k.c.C_Yetenek) k.c.C_Yetenek.cd[r.id] = y.cd;
      var hx = r.hedef ? r.hedef.x : p.x + (r.yon ? r.yon.x : p.dx) * 8, hz = r.hedef ? r.hedef.z : p.z + (r.yon ? r.yon.z : p.dz) * 8;
      var yon = r.yon ? norm(r.yon.x, r.yon.z) : norm(hx - p.x, hz - p.z, { x: p.dx, z: p.dz });
      p.dx = yon.x; p.dz = yon.z;
      var takim = k.c.C_Takim ? k.c.C_Takim.t : 'oyuncu';
      w.emit('cast', { kaynak: k, id: r.id, y: y, yon: yon, hedef: { x: hx, z: hz } });
      if (r.id === 'atis' || r.id === 'top') {
        w.olustur('mermi', { sahip: k, takim: takim, x: p.x + yon.x * 0.8, z: p.z + yon.z * 0.8, y: 1.15, dx: yon.x, dz: yon.z, hiz: y.hiz, hasar: y.hasar, element: y.element, omur: y.omur, r: y.r, tur: r.id });
      } else if (r.id === 'simsek') {
        simsekAt(w, k, y, yon, takim);
      } else if (r.id === 'firtina') {
        var dx = hx - p.x, dz = hz - p.z, dd = sqrt(dx * dx + dz * dz), kat = dd > y.menzil ? y.menzil / dd : 1;
        w.olustur('alan', { sahip: k, takim: takim, x: p.x + dx * kat, z: p.z + dz * kat, r: y.r, sure: y.sure, tick: y.tick, hasar: y.hasar, element: y.element, tur: 'firtina' });
      } else if (r.id === 'patlama') {
        var cx, cz;
        if (w.mod === 'kosu') { cx = p.x; cz = p.z - (y.ileri || 8); }
        else { var ddx = hx - p.x, ddz = hz - p.z, d2 = sqrt(ddx * ddx + ddz * ddz), kt = d2 > y.menzil ? y.menzil / d2 : 1; cx = p.x + ddx * kt; cz = p.z + ddz * kt; }
        w.emit('patlama', { x: cx, z: cz, r: y.r, element: y.element });
        hedefler(w, takim).forEach(function (h) {
          var hp = tf(h), dd2 = uzak(hp, { x: cx, z: cz });
          if (dd2 <= y.r + h.c.C_Cisim.r) {
            var o = norm(hp.x - cx, hp.z - cz);
            hasarIste(w, h, y.hasar * (1 - 0.4 * min(1, dd2 / y.r)), { kaynak: k, element: y.element, itme: { x: o.x, z: o.z, g: y.itme } });
          }
        });
      } else if (r.id === 'kalkan') {
        var d = k.c.C_Durum; d.kalkan = y.emilim; d.kalkanT = y.sure;
        w.emit('kalkan_acildi', { hedef: k, emilim: y.emilim, sure: y.sure });
      } else if (r.id === 'dash') {
        var dd0 = k.c.C_Durum; dd0.dokunulmaz = max(dd0.dokunulmaz, y.dokunulmaz);
        k.c.C_Atilma = { t: y.sure, dx: yon.x, dz: yon.z, hiz: y.hiz }; w.surum++;
        w.emit('atilma', { kaynak: k, yon: yon });
      }
    }
  }
  function simsekAt(w, k, y, yon, takim) {
    var p = tf(k), aday = hedefler(w, takim).filter(function (h) {
      if (w.mod !== 'kosu' && !h.c.C_YZ) return false;       // arenada sandıklara zincirlenmesin
      return true;
    });
    var ilk = null, en = 1e9;
    aday.forEach(function (h) {
      var hp = tf(h), dd = uzak(hp, p), ox = (hp.x - p.x), oz = (hp.z - p.z), cos = dd > 0.01 ? (ox * yon.x + oz * yon.z) / dd : 1;
      if (dd <= y.menzil && cos > 0.2 && dd < en) { en = dd; ilk = h; }
    });
    var noktalar = [{ x: p.x, y: 1.3, z: p.z }], vurulan = [];
    var son = ilk;
    while (son && vurulan.length < y.zincir) {
      vurulan.push(son);
      var sp = tf(son); noktalar.push({ x: sp.x, y: 1.0, z: sp.z });
      var sonraki = null, e2 = 1e9;
      aday.forEach(function (h) {
        if (vurulan.indexOf(h) >= 0) return;
        var dd = uzak(tf(h), sp);
        if (dd <= y.zincirMenzil && dd < e2) { e2 = dd; sonraki = h; }
      });
      son = sonraki;
    }
    if (!vurulan.length) noktalar.push({ x: p.x + yon.x * y.menzil * 0.55, y: 1.0, z: p.z + yon.z * y.menzil * 0.55 });
    vurulan.forEach(function (h, i) {
      hasarIste(w, h, y.hasar * Math.pow(0.82, i), { kaynak: k, element: y.element });
    });
    w.emit('simsek', { kaynak: k, noktalar: noktalar, vurulan: vurulan });
  }

  /* ======================= hareket, mermi, alan ======================= */
  function HareketSistemi(w, dt) {
    var R = w.durum.sinirR;
    w.sorgu(['C_Transform', 'C_Hiz']).forEach(function (e) {
      if (e.c.C_Mermi || e.c.C_Olu) return;
      var p = tf(e), h = e.c.C_Hiz, vx = h.vx, vz = h.vz;
      var a = e.c.C_Atilma;
      if (a) { vx = a.dx * a.hiz; vz = a.dz * a.hiz; a.t -= dt; if (a.t <= 0) { delete e.c.C_Atilma; w.surum++; } }
      var it = e.c.C_Itme;
      if (it) { vx += it.x; vz += it.z; var s = Math.exp(-7 * dt); it.x *= s; it.z *= s; if (Math.abs(it.x) + Math.abs(it.z) < 0.05) { it.x = 0; it.z = 0; } }
      p.x += vx * dt; p.z += vz * dt;
      if (R && e.c.C_Sinir) {
        var r = e.c.C_Cisim ? e.c.C_Cisim.r : 0.5, l = sqrt(p.x * p.x + p.z * p.z), lim = R - r;
        if (l > lim) { p.x *= lim / l; p.z *= lim / l; }
      }
    });
  }

  function segmentDaire(ax, az, bx, bz, cx, cz) {   // doğru parçası ile nokta arasındaki en kısa uzaklık
    var dx = bx - ax, dz = bz - az, l2 = dx * dx + dz * dz, t = l2 > 0 ? ((cx - ax) * dx + (cz - az) * dz) / l2 : 0;
    t = t < 0 ? 0 : (t > 1 ? 1 : t);
    var px = ax + dx * t - cx, pz = az + dz * t - cz;
    return sqrt(px * px + pz * pz);
  }
  function MermiSistemi(w, dt) {
    var R = w.durum.sinirR;
    w.sorgu(['C_Mermi', 'C_Transform']).forEach(function (e) {
      if (e.olu) return;
      var m = e.c.C_Mermi, p = tf(e);
      m.px = p.x; m.pz = p.z;
      p.x += p.dx * m.hiz * dt; p.z += p.dz * m.hiz * dt; m.omur -= dt;
      var hs = hedefler(w, m.takim), vurdu = false;
      for (var i = 0; i < hs.length; i++) {
        var h = hs[i];
        if (m.vurdu[h.id]) continue;
        var hp = tf(h);
        if (segmentDaire(m.px, m.pz, p.x, p.z, hp.x, hp.z) <= m.r + h.c.C_Cisim.r) {
          m.vurdu[h.id] = 1; vurdu = true;
          hasarIste(w, h, m.hasar, { kaynak: m.sahip, element: m.element, itme: { x: p.dx, z: p.dz, g: m.tur === 'top' ? 5 : 2.5 } });
          w.emit('mermi_vurdu', { x: hp.x, z: hp.z, element: m.element, tur: m.tur });
          if (!m.delici) break;
        }
      }
      if (vurdu && !m.delici) { w.yoket(e); return; }
      if (m.omur <= 0 || (R && sqrt(p.x * p.x + p.z * p.z) > R + 2)) { w.emit('mermi_sondu', { x: p.x, z: p.z, tur: m.tur }); w.yoket(e); }
    });
  }
  function AlanSistemi(w, dt) {
    w.sorgu(['C_Alan', 'C_Transform']).forEach(function (e) {
      if (e.olu) return;
      var a = e.c.C_Alan, p = tf(e);
      a.sure -= dt; a.tickT -= dt;
      if (a.tickT <= 0) {
        a.tickT += a.tick;
        hedefler(w, a.takim).forEach(function (h) {
          if (uzak(tf(h), p) <= a.r + h.c.C_Cisim.r) hasarIste(w, h, a.hasar, { kaynak: a.sahip, element: a.element, tur: 'alan' });
        });
      }
      if (a.sure <= 0) { w.emit('alan_bitti', { x: p.x, z: p.z, tur: a.tur }); w.yoket(e); }
    });
  }

  /* ======================= yapay zeka (Reia: 15 m görüş) ======================= */
  function YapayZekaSistemi(w, dt) {
    var oy = oyuncular(w), liste = w.sorgu(['C_YZ', 'C_Transform', 'C_Can', 'C_Hiz']).filter(function (e) { return !e.c.C_Olu; });
    liste.forEach(function (e) {
      var yz = e.c.C_YZ, p = tf(e), h = e.c.C_Hiz, d = V.DUSMAN[yz.tip], dr = e.c.C_Durum;
      yz.bekleme -= dt; if (yz.vurusT > 0) yz.vurusT -= dt;
      h.vx = 0; h.vz = 0;
      if (dr && dr.stun > 0) return;
      var hedef = null, en = 1e9;
      oy.forEach(function (o) { var dd = uzak(tf(o), p); if (dd < en) { en = dd; hedef = o; } });
      if (!hedef) return;
      var hp = tf(hedef), yon = norm(hp.x - p.x, hp.z - p.z);
      if (yz.durum === 'bekle') {
        if (en <= d.aggro) { yz.durum = 'kovala'; w.emit('fark_etti', { varlik: e }); }
        return;
      }
      if (d.boss) {
        var oran = e.c.C_Can.hp / e.c.C_Can.max, es = [0.66, 0.33];
        for (var i = 0; i < 2; i++) if (!yz.esik[i] && oran <= es[i]) {
          yz.esik[i] = true;
          for (var j = 0; j < 3; j++) { var a = w.rastgele() * 6.28; w.olustur('dusman', { tip: 'jole', x: p.x + Math.cos(a) * 2.6, z: p.z + Math.sin(a) * 2.6, dalga: w.durum.dalga ? w.durum.dalga.no : 1 }); }
          w.emit('dusman_dogur', { varlik: e });
        }
      }
      if (yz.durum === 'kovala') {
        p.dx = yon.x; p.dz = yon.z;
        var hiz = d.hiz * (dr && dr.islak > 0 ? 0.9 : 1);
        if (d.tip === 'slime') hiz *= 0.2 + 2.2 * max(0, sin(w.zaman * 5 + yz.faz));
        if (en > hedef.c.C_Cisim.r + e.c.C_Cisim.r + 0.15) { h.vx = yon.x * hiz; h.vz = yon.z * hiz; }
        if (d.tip === 'goblin' && en <= d.menzil && yz.bekleme <= 0) { yz.durum = 'hazirla'; yz.t = d.hazirlik; w.emit('saldiri_hazirlik', { varlik: e, sure: d.hazirlik }); }
        else if (d.tip === 'kral' && yz.vurusT <= 0 && en < 16) { yz.durum = 'vurus_hazirla'; yz.t = d.vurusHazirlik; w.emit('yere_vurus_hazirlik', { varlik: e, r: d.vurusR, sure: d.vurusHazirlik }); }
        else if ((d.tip === 'slime' || d.tip === 'kral') && en <= hedef.c.C_Cisim.r + e.c.C_Cisim.r + 0.2 && yz.bekleme <= 0) {
          hasarIste(w, hedef, d.temas, { kaynak: e, itme: { x: yon.x, z: yon.z, g: 7 } });
          yz.bekleme = d.temasBekle; w.emit('dusman_vurdu', { varlik: e });
        }
      } else if (yz.durum === 'hazirla') {
        yz.t -= dt;
        if (yz.t <= 0) {
          if (en <= d.menzil * 1.35) { hasarIste(w, hedef, d.hasar, { kaynak: e, itme: { x: yon.x, z: yon.z, g: 8 } }); w.emit('dusman_vurdu', { varlik: e }); }
          yz.bekleme = d.bekle; yz.durum = 'kovala';
        }
      } else if (yz.durum === 'vurus_hazirla') {
        yz.t -= dt;
        if (yz.t <= 0) {
          w.emit('yere_vurus', { varlik: e, x: p.x, z: p.z, r: d.vurusR });
          oy.forEach(function (o) {
            var dd = uzak(tf(o), p);
            if (dd <= d.vurusR + o.c.C_Cisim.r) { var y2 = norm(tf(o).x - p.x, tf(o).z - p.z); hasarIste(w, o, d.vurusHasar, { kaynak: e, itme: { x: y2.x, z: y2.z, g: 11 } }); }
          });
          yz.vurusT = d.vurusAralik; yz.durum = 'kovala';
        }
      }
    });
    // üst üste binmeyi azalt
    for (var a = 0; a < liste.length; a++) {
      for (var b = a + 1; b < liste.length; b++) {
        var pa = tf(liste[a]), pb = tf(liste[b]), ra = liste[a].c.C_Cisim.r, rb = liste[b].c.C_Cisim.r;
        var dx = pb.x - pa.x, dz = pb.z - pa.z, dd = sqrt(dx * dx + dz * dz), minD = (ra + rb) * 0.9;
        if (dd < minD && dd > 1e-4) {
          var it = (minD - dd) * 0.5, ux = dx / dd, uz = dz / dd;
          pa.x -= ux * it; pa.z -= uz * it; pb.x += ux * it; pb.z += uz * it;
        }
      }
    }
  }

  /* ======================= dalgalar (Arena) ======================= */
  function dalgaPlani(n) {
    var plan = [], jole = Math.min(16, 3 + Math.floor(n * 1.2)), gob = n >= 2 ? Math.min(10, Math.floor((n - 1) * 0.9)) : 0, boss = n % 5 === 0;
    if (boss) { jole = Math.ceil(jole / 2); gob = Math.ceil(gob / 2); plan.push('kral'); }
    for (var i = 0; i < jole; i++) plan.push('jole');
    for (var j = 0; j < gob; j++) plan.push('goblin');
    // karıştır (deterministik değil, mod rastgelesi)
    return { liste: plan, boss: boss };
  }
  function DalgaSistemi(w, dt) {
    var ds = w.durum.dalga;
    if (!ds || w.durum.bitti) return;
    ds.saat += dt;
    for (var i = ds.kuyruk.length - 1; i >= 0; i--) {
      var q = ds.kuyruk[i];
      if (q.t <= ds.saat) {
        ds.kuyruk.splice(i, 1);
        var a = w.rastgele() * 6.2832, R = (w.durum.sinirR || 22) - 2.2;
        w.olustur('dusman', { tip: q.tip, x: Math.cos(a) * R, z: Math.sin(a) * R, dalga: ds.no });
        w.emit('dusman_dogdu', { tip: q.tip });
      }
    }
    var canli = w.sorgu(['C_YZ']).filter(function (e) { return !e.c.C_Olu; }).length;
    if (!ds.aktif) {
      ds.bekle -= dt;
      if (ds.bekle <= 0) {
        ds.no++; ds.aktif = true; ds.saat = 0;
        var pl = dalgaPlani(ds.no), t = 0.2;
        pl.liste.sort(function () { return w.rastgele() - 0.5; });
        if (pl.boss) pl.liste.sort(function (a, b) { return (a === 'kral' ? -1 : 0) - (b === 'kral' ? -1 : 0); });
        pl.liste.forEach(function (tip) { ds.kuyruk.push({ t: t, tip: tip }); t += tip === 'kral' ? 2.2 : 0.38; });
        ds.boss = pl.boss;
        w.emit('dalga_basladi', { no: ds.no, boss: pl.boss, adet: pl.liste.length });
      }
    } else if (!ds.kuyruk.length && canli === 0) {
      ds.aktif = false; ds.bekle = 4.2;
      var bonus = 50 * ds.no + (ds.boss ? 250 : 0);
      w.durum.skor += bonus;
      w.emit('dalga_bitti', { no: ds.no, bonus: bonus });
      // sunak yeniden kullanılabilir (iki dalgada bir)
      if (ds.no % 2 === 0) w.sorgu(['C_Etkilesim']).forEach(function (e) { if (e.c.C_Etkilesim.tip === 'sunak') e.c.C_Etkilesim.hazir = true; });
    }
  }

  /* ======================= toplanır / etkileşim ======================= */
  function ToplanirSistemi(w, dt) {
    var oy = oyuncular(w);
    w.sorgu(['C_Toplanir', 'C_Transform']).forEach(function (e) {
      if (e.olu) return;
      var t = e.c.C_Toplanir, p = tf(e);
      t.omur -= dt;
      if (t.omur <= 0) { w.yoket(e); return; }
      for (var i = 0; i < oy.length; i++) {
        var o = oy[i], op = tf(o), dd = uzak(op, p);
        if (dd < 4.2 && t.omur < 13.7) { var y = norm(op.x - p.x, op.z - p.z); var sp = 9 * (1 - dd / 5); p.x += y.x * sp * dt; p.z += y.z * sp * dt; }
        if (dd < 1.0) {
          if (t.tur === 'cekirdek' && o.c.C_Ether) o.c.C_Ether.v = min(o.c.C_Ether.max, o.c.C_Ether.v + t.deger);
          else if (t.tur === 'kalp') o.c.C_Can.hp = min(o.c.C_Can.max, o.c.C_Can.hp + t.deger);
          w.emit('toplandi', { tur: t.tur, deger: t.deger, x: p.x, z: p.z });
          w.yoket(e); return;
        }
      }
    });
  }
  function EtkilesimSistemi(w, dt) {
    var oy = oyuncular(w)[0];
    w.durum.etkilesim = null; w.durum.ocakta = false;
    if (!oy) return;
    var op = tf(oy), en = 1e9, enE = null;
    w.sorgu(['C_Etkilesim', 'C_Transform']).forEach(function (e) {
      var et = e.c.C_Etkilesim, dd = uzak(tf(e), op);
      if (dd > et.menzil) return;
      if (et.tip === 'ocak') { w.durum.ocakta = true; var s = oy.c.C_Ether; if (s) s.v = min(s.max, s.v + 16 * dt); }
      else if (et.hazir && dd < en) { en = dd; enE = e; }
    });
    if (enE) w.durum.etkilesim = { varlik: enE, tip: enE.c.C_Etkilesim.tip };
    w.tuket('etkilesim').forEach(function () {
      var h = w.durum.etkilesim;
      if (!h) return;
      if (h.tip === 'sunak') {
        h.varlik.c.C_Etkilesim.hazir = false;
        oy.c.C_Durum.guc = 20;
        oy.c.C_Can.hp = min(oy.c.C_Can.max, oy.c.C_Can.hp + 30);
        oy.c.C_Ether.v = oy.c.C_Ether.max;
        w.emit('sunak_kullanildi', { x: tf(h.varlik).x, z: tf(h.varlik).z });
      }
    });
  }

  /* ======================= ölüm / puan / düşenler ======================= */
  var puanKomboZaman = 2.6;
  function puanEkle(w, deger, x, z) {
    var d = w.durum;
    if (d.kombo === undefined) { d.kombo = 0; d.komboT = 0; d.skor = d.skor || 0; }
    d.kombo++; d.komboT = puanKomboZaman;
    var carpan = min(3, 1 + Math.floor(d.kombo / 5) * 0.25);
    var kazan = Math.round(deger * carpan);
    d.skor += kazan;
    w.emit('puan', { deger: kazan, taban: deger, carpan: carpan, x: x, z: z, kombo: d.kombo });
  }
  function OlumSistemi(w, dt) {
    var d = w.durum;
    if (d.komboT > 0) { d.komboT -= dt; if (d.komboT <= 0) d.kombo = 0; }
    w.sorgu(['C_Olu']).forEach(function (e) {
      var o = e.c.C_Olu;
      if (o.isl) return;
      o.isl = true;
      var p = tf(e);
      w.emit('olum', { varlik: e, katil: o.katil });
      if (e.c.C_Puan) puanEkle(w, e.c.C_Puan.deger, p.x, p.z);
      if (e.c.C_YZ) {
        var dd = V.DUSMAN[e.c.C_YZ.tip];
        var n = dd.boss ? 6 : 1;
        for (var i = 0; i < n; i++) w.olustur('toplanir', { tur: 'cekirdek', deger: dd.ether / n * (dd.boss ? 1 : 1), x: p.x + (w.rastgele() - 0.5) * 1.6, z: p.z + (w.rastgele() - 0.5) * 1.6 });
        if (dd.boss || w.rastgele() < 0.14) w.olustur('toplanir', { tur: 'kalp', deger: dd.boss ? 50 : 22, x: p.x, z: p.z });
      } else if (e.c.C_Prop && e.c.C_Prop.tip === 'sandik') {
        w.olustur('toplanir', { tur: 'kalp', deger: 30, x: p.x - 0.5, z: p.z });
        w.olustur('toplanir', { tur: 'cekirdek', deger: 40, x: p.x + 0.5, z: p.z });
      }
      if (e.c.C_Oyuncu) { d.bitti = true; w.emit('oyuncu_oldu', { varlik: e }); }
      else w.yoket(e);
    });
  }

  /* ======================= kurulum ======================= */
  function kur(w, ayar) {
    ayar = ayar || {};
    w.durum.skor = 0; w.durum.kombo = 0; w.durum.komboT = 0; w.durum.bitti = false;
    prefablariKur(w);
    w.sistemEkle('DurumSistemi', DurumSistemi, 10);
    w.sistemEkle('YenilemeSistemi', YenilemeSistemi, 15);
    if (w.mod === 'arena') {
      w.durum.sinirR = ayar.sinirR || 22;
      w.durum.dalga = { no: 0, aktif: false, bekle: 2.6, kuyruk: [], saat: 0, boss: false };
      w.sistemEkle('DalgaSistemi', DalgaSistemi, 20);
      w.sistemEkle('YapayZekaSistemi', YapayZekaSistemi, 30);
      w.sistemEkle('ToplanirSistemi', ToplanirSistemi, 60);
      w.sistemEkle('EtkilesimSistemi', EtkilesimSistemi, 62);
    }
    w.sistemEkle('CastSistemi', CastSistemi, 40);
    w.sistemEkle('HareketSistemi', HareketSistemi, 50);
    w.sistemEkle('MermiSistemi', MermiSistemi, 55);
    w.sistemEkle('AlanSistemi', AlanSistemi, 56);
    w.sistemEkle('HasarSistemi', HasarSistemi, 70);
    w.sistemEkle('OlumSistemi', OlumSistemi, 80);
    return w;
  }

  NS.sistemler = {
    kur: kur, hasarIste: hasarIste, castIste: castIste, castDurumu: castDurumu, dalgaPlani: dalgaPlani,
    puanEkle: puanEkle, hedefler: hedefler, oyuncular: oyuncular, norm: norm, uzak: uzak, itmeUygula: itmeUygula, tepkimeBul: tepkimeBul
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = NS;
})(typeof window !== 'undefined' ? window : globalThis);
