/* Geek Oyun · arayüz katmanı (Reia'nın atomik yapısı)
   atomlar: buton, ikon, çubuk, rozet · moleküller: durum satırı, yetenek yuvası · organizmalar: HUD, eylem çubuğu, joystick
   ekranlar: başlık menüsü, duraklat, oyun sonu, ayarlar, rehber, dolap iskeleti. Oyun mantığını bilmez; olayları üst katmana iletir. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var V = NS.veri;

  /* ---------------- atomlar ---------------- */
  var YOL = {
    top: 'M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-9z',
    simsek: 'M13 2 4 14h7l-1 8 9-12h-7z',
    firtina: 'M7 15a4 4 0 0 1 0-8 5 5 0 0 1 9.5 1A3.5 3.5 0 0 1 17 15M8 18l-1 3M12 18l-1 3M16 18l-1 3',
    patlama: 'M12 2v5M12 17v5M2 12h5M17 12h5M5 5l3.5 3.5M15.5 15.5 19 19M5 19l3.5-3.5M15.5 8.5 19 5',
    kalkan: 'M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z',
    dash: 'M4 12h12M12 6l6 6-6 6M3 7v10',
    atis: 'M5 8h11v7a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4zM16 10h2a2 2 0 0 1 0 5h-2M8 3v2M12 3v2',
    ses: 'M4 9v6h4l5 4V5L8 9zM16 9a4 4 0 0 1 0 6',
    radyo: 'M4 9h16v11H4zM7 9l10-5M8 14.5h5M17 13.5v2',
    durdur: 'M8 5v14M16 5v14',
    tam: 'M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5',
    cik: 'M9 4H5v16h4M14 8l4 4-4 4M18 12H9'
  };
  var DOLU = {
    kalp: 'M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2.5 4.5-9.5 9-9.5 9z',
    ether: 'M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z',
    stamina: 'M13 2 5 13h6l-1 9 9-12h-6z'
  };
  function svgCizgi(ad) { return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + (YOL[ad] || YOL.atis) + '"/></svg>'; }
  function svgDolu(ad) { return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + DOLU[ad] + '"/></svg>'; }

  function el(tag, sinif, ozellik, ic) {
    var e = document.createElement(tag);
    if (sinif) e.className = sinif;
    if (ozellik) for (var k in ozellik) { if (k === 'metin') e.textContent = ozellik[k]; else if (k === 'html') e.innerHTML = ozellik[k]; else e.setAttribute(k, ozellik[k]); }
    if (ic) (Array.isArray(ic) ? ic : [ic]).forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }
  function buton(metin, tur, fn, ek) {
    var b = el('button', 'go-buton' + (tur ? ' ' + tur : ''), { type: 'button', metin: metin });
    if (ek) for (var k in ek) b.setAttribute(k, ek[k]);
    if (fn) b.addEventListener('click', fn);
    return b;
  }
  function ikonButon(ikon, etiket, fn, ek) {
    var b = el('button', 'go-ikon-buton', { type: 'button', 'aria-label': etiket, title: etiket, html: svgCizgi(ikon) });
    if (ek) for (var k in ek) b.setAttribute(k, ek[k]);
    if (fn) b.addEventListener('click', fn);
    return b;
  }
  function chip(html) { return el('span', 'go-chip', { html: html }); }
  function cubuk(tur) {
    var dolgu = el('i'), kalkan = el('span', 'go-kalkan'), k = el('div', 'go-cubuk ' + tur, null, [dolgu, kalkan]);
    k._d = dolgu; k._k = kalkan; return k;
  }

  /* ---------------- moleküller ---------------- */
  function durumSatiri(tur, simge) {
    var c = cubuk(tur), out = el('output', null, { metin: '0' });
    var s = el('div', 'go-durum-satir ' + tur, null, [el('span', null, { html: svgDolu(simge) }), c, out]);
    s._c = c; s._o = out; return s;
  }
  function yetenekYuvasi(id, mod, fn) {
    var y = V.yetenek(id, mod), tus = V.TUS[mod].tus[id];
    var b = el('button', 'go-slot ' + (y.element || id), { type: 'button', 'aria-label': y.ad + ' (' + tus + ')', title: y.ad + ' · ' + tus + (y.maliyet ? ' · ' + y.maliyet + (y.kaynak === 'ether' ? ' ether' : ' dayanıklılık') : '') });
    b.innerHTML = svgCizgi(id) + '<span class="go-tus">' + tus + '</span>' + (y.maliyet ? '<span class="go-mal">' + y.maliyet + '</span>' : '');
    b.dataset.id = id;
    b.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); fn(id); b.classList.remove('bas'); void b.offsetWidth; b.classList.add('bas'); });
    b.addEventListener('keydown', function (e) { if (e.code === 'Space' || e.code === 'Enter') e.preventDefault(); });
    return b;
  }

  /* ---------------- kur ---------------- */
  NS.ui = {
    kur: function (kok, ayar) {
      var olay = ayar.olay || function () {};
      var ui = {}, ekranlar = {}, aktifEkran = null, mod = 'kosu';
      var mount = el('div', 'go-ui'); kok.appendChild(mount);
      var metin = ayar.metin || {};

      /* ============ HUD ============ */
      var hud = el('div', 'go-hud'); hud.hidden = true; mount.appendChild(hud);
      var sCan = durumSatiri('can', 'kalp'), sEther = durumSatiri('ether', 'ether'), sStam = durumSatiri('stamina', 'stamina');
      var guclar = el('div', 'go-guclar');
      var panelStat = el('div', 'go-panel go-stat', null, [sCan, sEther, sStam, guclar]);
      var ustBaslik = el('div', 'go-baslik'), ustCubuk = cubuk('seviye');
      var ustOrta = el('div', 'go-ust-orta', null, [ustBaslik, ustCubuk]);
      var bossBaslik = el('div', 'go-baslik'), bossCubuk = cubuk('boss');
      var bossKutu = el('div', 'go-ust-orta go-boss', null, [bossBaslik, bossCubuk]); bossKutu.hidden = true; bossKutu.style.top = 'calc(max(12px,env(safe-area-inset-top)) + 52px)';
      var skor = el('div', 'go-skor', { metin: '0' });
      var komboChip = chip(''), cekChip = chip(''); komboChip.hidden = true;
      var skorAlt = el('div', 'go-skor-alt', null, [komboChip, cekChip]);
      var butonlar = el('div', 'go-butonlar');
      var bRadyo = ikonButon('radyo', 'Geek Radio', null, { 'data-kosu-radyo': 'hud', 'aria-pressed': 'false' });
      var bSes = ikonButon('ses', 'Ses efektleri', function () { olay('ses'); }, { 'aria-pressed': 'true' });
      var bTam = ikonButon('tam', 'Tam ekran', function () { olay('tamekran'); });
      var bDur = ikonButon('durdur', 'Duraklat', function () { olay('duraklat'); });
      var bCik = ikonButon('cik', 'Ana menüye dön', function () { olay('menu'); });
      [bRadyo, bSes, bTam, bDur, bCik].forEach(function (b) { butonlar.appendChild(b); });
      var sagUst = el('div', 'go-sag-ust', null, [skor, skorAlt, butonlar]);
      var eylem = el('div', 'go-eylem'), ipucu = el('button', 'go-ipucu', { type: 'button' }); ipucu.hidden = true;
      var alt = el('div', 'go-alt', null, [ipucu, eylem]);
      var gunluk = el('div', 'go-gunluk');
      var radyoBilgi = el('div', 'go-radyo-bilgi', { 'data-kosu-radyo-bilgi': '' }); radyoBilgi.hidden = true;
      var mesaj = el('div', 'go-mesaj', { role: 'status', 'aria-live': 'polite' });
      var geri = el('div', 'go-geri', { 'aria-live': 'assertive' });
      var joy = el('div', 'go-joy', null, [el('i')]);
      [panelStat, ustOrta, bossKutu, sagUst, gunluk, alt, radyoBilgi, mesaj, geri, joy].forEach(function (x) { hud.appendChild(x); });
      ipucu.addEventListener('pointerdown', function (e) { e.preventDefault(); e.stopPropagation(); olay('etkilesim'); });
      var yuvalar = {};
      var onb = {};   // son yazılan değerler: DOM yalnız değişince güncellenir
      function yaz(anahtar, deger, fn) { if (onb[anahtar] !== deger) { onb[anahtar] = deger; fn(deger); } }

      ui.hud = {
        goster: function (acik, yeniMod) {
          hud.hidden = !acik;
          if (yeniMod && yeniMod !== mod || (yeniMod && !eylem.firstChild)) {
            mod = yeniMod; eylem.innerHTML = ''; yuvalar = {};
            V.TUS[mod].sira.forEach(function (id) { var b = yetenekYuvasi(id, mod, function (i) { olay('cast', i); }); yuvalar[id] = b; eylem.appendChild(b); });
            onb = {};
          }
          if (yeniMod) { mod = yeniMod; ustCubuk.hidden = false; }
          if (!acik) { mesaj.classList.remove('goster'); geri.textContent = ''; }
        },
        guncelle: function (d) {
          yaz('can', Math.ceil(d.can) + '/' + d.canMax, function () {
            sCan._c._d.style.width = (d.can / d.canMax * 100).toFixed(1) + '%'; sCan._o.textContent = Math.ceil(d.can);
            sCan._c.classList.toggle('az', d.can / d.canMax < 0.3);
          });
          yaz('kalkan', Math.ceil(d.kalkan || 0), function (v) { sCan._c._k.style.width = Math.min(100, v / d.canMax * 100) + '%'; });
          yaz('ether', Math.floor(d.ether), function (v) { sEther._c._d.style.width = (d.ether / d.etherMax * 100).toFixed(1) + '%'; sEther._o.textContent = v; });
          yaz('stam', Math.floor(d.stamina), function (v) { sStam._c._d.style.width = (d.stamina / d.staminaMax * 100).toFixed(1) + '%'; sStam._o.textContent = v; });
          yaz('skor', d.skor, function (v) { skor.textContent = v; });
          yaz('cek', d.cekirdek + '|' + (d.cekEtiket || ''), function () { cekChip.innerHTML = '<b>' + d.cekirdek + '</b> ' + (d.cekEtiket || 'çekirdek'); });
          yaz('kombo', d.kombo > 1 ? d.kombo + '|' + d.carpan : '', function (v) {
            komboChip.hidden = !v; if (v) komboChip.innerHTML = 'Seri <b>' + d.kombo + '</b>' + (d.carpan > 1 ? ' · x' + d.carpan : '');
          });
          yaz('ust', d.ust ? d.ust.baslik : '', function (v) { ustBaslik.textContent = v; });
          yaz('ustO', d.ust ? Math.round(d.ust.oran * 500) : -1, function () { ustCubuk._d.style.width = (d.ust ? d.ust.oran * 100 : 0).toFixed(1) + '%'; });
          yaz('boss', d.boss ? d.boss.ad + Math.ceil(d.boss.oran * 200) : '', function () {
            bossKutu.hidden = !d.boss; if (d.boss) { bossBaslik.textContent = d.boss.ad; bossCubuk._d.style.width = (d.boss.oran * 100).toFixed(1) + '%'; }
          });
          var cd = d.cd || {};
          for (var id in yuvalar) {
            var c = cd[id] || { oran: 0, yetersiz: false, kapali: false };
            var b = yuvalar[id], o = Math.round(c.oran * 100);
            yaz('cd' + id, o + (c.yetersiz ? 'y' : '') + (c.kapali ? 'k' : ''), function () {});
            if (b._o !== o) { b._o = o; b.style.setProperty('--cd', o + '%'); }
            var sn = (c.oran > 0 ? 'bekle' : (c.yetersiz ? 'yetersiz' : 'hazir')) + (c.kapali ? ' kapali' : '');
            if (b._s !== sn) { b._s = sn; b.classList.toggle('hazir', sn.indexOf('hazir') === 0); b.classList.toggle('yetersiz', sn.indexOf('yetersiz') === 0); b.classList.toggle('kapali', !!c.kapali); }
          }
          (d.guclar || []).forEach(function (g) {
            var k = ui._guc[g.id];
            if (!k) {
              var c2 = cubuk('seviye'); c2._d.style.background = g.renk;
              k = ui._guc[g.id] = { kap: el('div', 'go-guc', null, [el('span', null, { metin: g.ad }), c2]), c: c2 }; k.kap.hidden = true; k.kap.style.color = g.renk; guclar.appendChild(k.kap);
            }
            var a = g.oran > 0; if (k.kap.hidden === a) k.kap.hidden = !a;
            if (a) k.c._d.style.width = (g.oran * 100).toFixed(1) + '%';
          });
          ipucu.hidden = !d.ipucu;
          if (d.ipucu && ipucu._t !== d.ipucu) { ipucu._t = d.ipucu; ipucu.innerHTML = '<kbd class="go-tus">' + (d.ipucuTus || 'E') + '</kbd>' + d.ipucu; }
        }
      };
      ui._guc = {};
      ui.guclariSifirla = function () { guclar.innerHTML = ''; ui._guc = {}; onb = {}; };
      ui.mesaj = function (m, ms, buyuk) {
        mesaj.textContent = m; mesaj.classList.toggle('buyuk', !!buyuk); mesaj.classList.add('goster');
        clearTimeout(ui._mt); ui._mt = setTimeout(function () { mesaj.classList.remove('goster'); }, ms || 1400);
      };
      ui.geri = function (m) { geri.textContent = m; geri.classList.remove('vur'); void geri.offsetWidth; if (m) geri.classList.add('vur'); };
      ui.gunluk = function (m, tur) {
        var d = el('div', tur || '', { metin: m }); gunluk.appendChild(d);
        while (gunluk.children.length > 5) gunluk.removeChild(gunluk.firstChild);
        setTimeout(function () { if (d.parentNode) d.parentNode.removeChild(d); }, 6100);
      };
      ui.sesDurumu = function (acik) { bSes.setAttribute('aria-pressed', acik ? 'true' : 'false'); bSes.title = acik ? 'Ses efektleri açık' : 'Ses efektleri kapalı'; };
      ui.yarali = function () { kok.classList.remove('yarali'); void kok.offsetWidth; kok.classList.add('yarali'); };
      ui.azCan = function (a) { kok.classList.toggle('az-can', !!a); };
      ui.joy = { x: 0, z: 0, aktif: false, etkin: false };
      ui.joyEtkin = function (a) { ui.joy.etkin = !!a; if (!a) { ui.joy.aktif = false; ui.joy.x = 0; ui.joy.z = 0; joy.classList.remove('acik'); } };

      /* joystick: sahnenin sol yarısına dokunuşla (yalnız dokunmatik / kalem) */
      (function () {
        var sahne = ayar.sahne, id = null, ox = 0, oy = 0, R = 52;
        function bitir() { id = null; ui.joy.aktif = false; ui.joy.x = 0; ui.joy.z = 0; joy.classList.remove('acik'); joy.firstChild.style.transform = ''; }
        sahne.addEventListener('pointerdown', function (e) {
          if (!ui.joy.etkin || e.pointerType === 'mouse' || id !== null || e.clientX > sahne.clientWidth * 0.62) return;
          id = e.pointerId; ox = e.clientX; oy = e.clientY; ui.joy.aktif = true;
          var r = kok.getBoundingClientRect();
          joy.style.left = (ox - r.left - 60) + 'px'; joy.style.bottom = (r.bottom - oy - 60) + 'px'; joy.classList.add('acik');
          try { sahne.setPointerCapture(id); } catch (x) {}
        });
        sahne.addEventListener('pointermove', function (e) {
          if (e.pointerId !== id) return;
          var dx = e.clientX - ox, dy = e.clientY - oy, l = Math.sqrt(dx * dx + dy * dy);
          if (l > R) { dx *= R / l; dy *= R / l; l = R; }
          ui.joy.x = dx / R; ui.joy.z = dy / R;
          joy.firstChild.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
        });
        sahne.addEventListener('pointerup', function (e) { if (e.pointerId === id) bitir(); });
        sahne.addEventListener('pointercancel', function (e) { if (e.pointerId === id) bitir(); });
      })();

      /* ============ EKRANLAR ============ */
      function ekran(ad, sinif, ic) { var e = el('section', 'go-ekran ' + sinif, { 'aria-label': ad }, ic); e.hidden = true; mount.appendChild(e); ekranlar[ad] = e; return e; }
      function radyoSatiri() {
        var b = buton('♪ Geek Radio\'yu aç', 'ikincil', null, { 'data-kosu-radyo': 'menu', 'aria-pressed': 'false' });
        var bilgi = el('div', 'go-radyo-bilgi-satir', { 'data-kosu-radyo-bilgi': '' }); bilgi.hidden = true;
        return el('div', 'go-radyo-satir', null, [b, bilgi]);
      }

      /* başlık menüsü */
      var kKosu = el('button', 'go-kart', { type: 'button' });
      kKosu.innerHTML = '<span class="go-bant">3 şeritli</span><h3>Koşu</h3><span class="go-alt-yazi">Sonsuz sokak. Zıpla, kay, hızlan.<br><b data-en="kosu"></b></span>';
      var kBilgi = el('button', 'go-kart bilgi', { type: 'button' });
      kBilgi.innerHTML = '<span class="go-bant">1000+ soru</span><h3>Bilgi Yarışması</h3><span class="go-alt-yazi">İlk yanlışta biter. Doğrusunu öğren.<br><b data-en="bilgi"></b></span>';
      kBilgi.addEventListener('click', function () { olay('basla', 'bilgi'); });
      kKosu.addEventListener('click', function () { olay('basla', 'kosu'); });
      var logo = el('div', 'go-logo', null, [ayar.logo ? el('img', null, { src: ayar.logo, alt: 'Geek', height: 44 }) : null, el('span', null, { metin: 'Oyun Salonu' })]);
      var geriPanel = buton('‹ Geri dön', 'ikincil go-geri-panel', function () { olay('cik'); });
      geriPanel.setAttribute('aria-label', 'Panele geri dön');
      var menu = el('div', 'go-menu', null, [
        geriPanel,
        logo,
        el('h1', null, { html: 'Barista<br><em>göreve hazır</em>' }),
        el('p', 'go-alt-yazi', { metin: 'Sokakta koş ya da Bilgi Yarışması\'nda bilgini sına. Skorların Oyun Salonu sıralamasına yazılır.' }),
        el('div', 'go-modlar', null, [kKosu, kBilgi]),
        el('div', 'go-ikinci', null, [buton('Dolap', 'ikincil', function () { olay('dolap'); }), buton('Rehber', 'ikincil', function () { olay('rehber'); }), buton('Ayarlar', 'ikincil', function () { olay('ayar'); })]),
        radyoSatiri()
      ]);
      ekran('menu', 'go-baslik-ekran', [menu]);
      ui.menuGuncelle = function (d) {
        [].forEach.call(menu.querySelectorAll('[data-en]'), function (b) { var v = b.dataset.en === 'kosu' ? d.enKosu : d.enBilgi; b.textContent = 'En iyi: ' + v; });
      };

      /* duraklat */
      ekran('dur', 'ortala', [el('div', 'go-kutu', null, [
        el('h2', null, { metin: 'Duraklatıldı' }),
        radyoSatiri(),
        el('div', 'go-aksiyon', null, [buton('Devam et', 'buyuk', function () { olay('devam'); }), buton('Ayarlar', 'ikincil', function () { olay('ayar'); }), buton('Ana menü', 'ikincil', function () { olay('menu'); }), buton('Panele dön', 'ikincil', function () { olay('cik'); })])
      ])]);

      /* oyun sonu */
      var bSkor = el('div', 'go-bitis-skor', { metin: '0' }), bBaslik = el('h2', null, { metin: 'Oyun bitti' }), bTablo = el('ul', 'go-tablo'), bRekor = el('div', 'go-rekor', { metin: 'Yeni kişisel rekor' }), bSira = el('div', 'go-sira');
      bRekor.hidden = true;
      ekran('bitis', 'ortala', [el('div', 'go-kutu', null, [bBaslik, bSkor, bRekor, bTablo, bSira,
        el('div', 'go-aksiyon', null, [buton('Tekrar oyna', 'buyuk', function () { olay('tekrar'); }), buton('Kıyafet değiştir', 'ikincil', function () { olay('dolap'); }), buton('Ana menü', 'ikincil', function () { olay('menu'); }), buton('Çık ve sıralamayı gör', 'ikincil', function () { olay('cik'); })])
      ])]);
      ui.bitis = {
        goster: function (d) {
          bBaslik.textContent = d.baslik || 'Oyun bitti'; bSkor.textContent = d.skor; bRekor.hidden = !d.rekor;
          bTablo.innerHTML = ''; d.satirlar.forEach(function (s) { bTablo.appendChild(el('li', null, null, [el('span', null, { metin: s[0] }), el('b', null, { metin: s[1] })])); });
          bSira.textContent = d.sira || '';
        },
        sira: function (m) { bSira.textContent = m; }
      };

      /* ayarlar */
      var ayarKap = el('div', 'go-kutu');
      ayarKap.appendChild(el('h2', null, { metin: 'Ayarlar' }));
      var ayarDeger = ayar.ayarlar || {};
      function ayarSatir(baslik, alt, anahtar, secenekler) {
        var seg = el('div', 'go-segment');
        secenekler.forEach(function (s) {
          var b = el('button', null, { type: 'button', metin: s[1] }); b.dataset.v = s[0];
          b.addEventListener('click', function () { ayarDeger[anahtar] = s[0]; yenile(); olay('ayarDegisti', { anahtar: anahtar, deger: s[0] }); });
          seg.appendChild(b);
        });
        function yenile() { [].forEach.call(seg.children, function (b) { b.setAttribute('aria-pressed', String(ayarDeger[anahtar]) === b.dataset.v ? 'true' : 'false'); }); }
        yenile();
        var l = el('div', 'go-ayar-satir', null, [el('span', null, { html: baslik + (alt ? '<small>' + alt + '</small>' : '') }), seg]);
        l._yenile = yenile; ayarKap.appendChild(l); return l;
      }
      var ayarSatirlari = [
        ayarSatir('Ses efektleri', '', 'ses', [['1', 'Açık'], ['0', 'Kapalı']]),
        ayarSatir('Grafik kalitesi', 'Otomatik, cihaza göre ayarlar', 'kalite', [['oto', 'Otomatik'], ['yuksek', 'Yüksek'], ['dengeli', 'Dengeli'], ['hafif', 'Hafif']]),
        ayarSatir('Titreşim', 'Dokunmatik cihazlarda', 'titresim', [['1', 'Açık'], ['0', 'Kapalı']]),
        ayarSatir('Kamera sarsıntısı', 'Çarpma ve patlamalarda', 'sarsinti', [['1', 'Açık'], ['0', 'Azaltılmış']])
      ];
      ayarKap.appendChild(buton('Tamam', 'buyuk', function () { olay('ayarKapat'); }));
      ekran('ayar', 'ortala', [ayarKap]);
      ui.ayarYenile = function () { ayarSatirlari.forEach(function (l) { l._yenile(); }); };

      /* rehber (kontroller · yetenekler · düşmanlar · elementler) */
      var rehberIc = el('ul', 'go-liste'), sekmeBar = el('div', 'go-sekmeler'), sekmeler = {};
      function rozet(sinif, ikonHtml) { return el('span', 'go-rozet ' + sinif, { html: ikonHtml }); }
      var REHBER = {
        kontrol: function () {
          return [
            ['Koşu', 'Sol/Sağ ya da A/D şerit değiştirir. Yukarı, W veya Boşluk zıplar (havada bir kez daha). Aşağı veya S kayar. Dokunmatik: kaydır, dokun = zıpla.'],
            ['Genel', 'P duraklat · R radyo aç/kapat · G dolap (menüde) · Esc duraklat.']
          ].map(function (r) { return el('li', null, null, [rozet('', svgCizgi('atis')), el('div', null, { html: '<b>' + r[0] + '</b><small>' + r[1] + '</small>' })]); });
        },
        yetenek: function () {
          return V.TUS.kosu.sira.map(function (id) {
            var y = V.YETENEK[id], tag = V.TUS.kosu.tus[id] ? 'Tuş ' + V.TUS.kosu.tus[id] : '';
            return el('li', null, null, [rozet(y.element || id, svgCizgi(id)), el('div', null, { html: '<b>' + y.ad + '</b><small>' + y.aciklama + ' · ' + (y.maliyet ? y.maliyet + (y.kaynak === 'ether' ? ' ether' : ' dayanıklılık') : 'bedava') + ' · ' + tag + '</small>' })]);
          });
        }
      };
      function rehberAc(ad) {
        rehberIc.innerHTML = ''; REHBER[ad]().forEach(function (x) { rehberIc.appendChild(x); });
        for (var k in sekmeler) sekmeler[k].setAttribute('aria-pressed', k === ad ? 'true' : 'false');
      }
      [['kontrol', 'Kontroller'], ['yetenek', 'Yetenekler']].forEach(function (s) {
        var b = buton(s[1], 'ikincil', function () { rehberAc(s[0]); }); b.style.minHeight = '36px'; b.style.padding = '0 12px'; b.style.fontSize = '12px'; sekmeler[s[0]] = b; sekmeBar.appendChild(b);
      });
      ekran('rehber', 'ortala', [el('div', 'go-kutu', null, [el('h2', null, { metin: 'Rehber' }), sekmeBar, rehberIc, buton('Tamam', 'buyuk', function () { olay('rehberKapat'); })])]);

      /* dolap iskeleti (içerik üst katmanda doldurulur) */
      var dolapKutu = el('div', 'kd-kutu', null, [
        el('div', 'kd-baslik', null, [el('h3', null, { metin: 'Dolap' }), buton('Hazır', null, function () { olay('dolapKapat'); }, { id: 'kd-bitti' })]),
        el('p', 'kd-ipucu', { metin: 'Barista\'nı sürükleyerek döndür. Yeni kıyafetler en iyi skorunla açılır.' }),
        el('div', 'kd-grup', null, [el('span', 'kd-et', { metin: 'Kıyafet' }), el('div', 'kd-izgara', { id: 'kd-kiyafet' })]),
        el('div', 'kd-grup', null, [el('span', 'kd-et', { metin: 'Ten rengi' }), el('div', 'kd-noktalar', { id: 'kd-ten' })]),
        el('div', 'kd-grup', null, [el('span', 'kd-et', { metin: 'Aksesuar' }), el('div', 'kd-cipler', { id: 'kd-aks' })])
      ]);
      ekran('dolap', 'go-dolap', [dolapKutu]);

      /* ekran yönetimi */
      ui.goster = function (ad) {
        for (var k in ekranlar) ekranlar[k].hidden = k !== ad;
        aktifEkran = ad;
        if (ad === 'rehber') rehberAc('kontrol');
        if (ad === 'ayar') ui.ayarYenile();
      };
      ui.aktif = function () { return aktifEkran; };
      ui.ayarlar = ayarDeger;
      return ui;
    }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = NS;
})(typeof window !== 'undefined' ? window : globalThis);
