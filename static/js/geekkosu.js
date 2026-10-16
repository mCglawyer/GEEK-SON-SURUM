/* Geek Koşusu — kahve/yemek engellerinden atlayan sonsuz koşu oyunu.
   Kontrol: Boşluk / ↑ / dokunma = zıpla (havadayken bir kez daha zıplanır). */
(function () {
  'use strict';
  var cv = document.getElementById('kosu-cv');
  if (!cv) return;
  var ctx = cv.getContext('2d');
  var W = 800, H = 340, YER = 280;
  var elSkor = document.getElementById('kosu-skor');
  var elEn = document.getElementById('kosu-en');
  var elSonuc = document.getElementById('kosu-sonuc');
  var csrf = (document.querySelector('input[name=csrfmiddlewaretoken]') || {}).value || '';
  var url = cv.getAttribute('data-skor-url');

  var CREMA = '#F2B544', NAVY = '#0B0F2E', MAVI = '#2F5BFF', KREM = '#FFF6E2';
  var durum = 'hazir';           // hazir | kosuyor | bitti
  var oyuncu, engeller, odul, hiz, mesafe, puanEk, sure, sonKare, bitisZamani;
  var enSkor = parseInt(cv.getAttribute('data-en') || '0', 10) || 0;
  var bulutlar = [], kareNo = 0;
  var havadaBasili = false;

  function sifirla() {
    oyuncu = { x: 90, y: YER - 46, w: 44, h: 46, vy: 0, yerde: true, ziplama: 0 };
    engeller = []; odul = [];
    hiz = 300; mesafe = 0; puanEk = 0; sure = 0; sonrakiEngel = 0.9;
    bulutlar = [];
    for (var i = 0; i < 5; i++) bulutlar.push({ x: Math.random() * W, y: 30 + Math.random() * 100, s: 0.5 + Math.random() * 0.6 });
  }
  var sonrakiEngel = 0.9;

  function skor() { return Math.floor(mesafe / 12) + puanEk; }

  function zipla() {
    if (durum === 'hazir') { basla(); }
    else if (durum === 'bitti') {
      if (performance.now() - bitisZamani > 450) basla();
      return;
    }
    if (oyuncu.yerde) { oyuncu.vy = -800; oyuncu.yerde = false; oyuncu.ziplama = 1; havadaBasili = true; }
    else if (oyuncu.ziplama < 2) { oyuncu.vy = -700; oyuncu.ziplama = 2; havadaBasili = true; }
  }
  function biraktim() {
    havadaBasili = false;
    if (oyuncu && oyuncu.vy < -280) oyuncu.vy = -280;   // kısa basış = kısa zıplama
  }

  function basla() {
    sifirla();
    durum = 'kosuyor'; sonKare = performance.now();
    elSonuc.textContent = ''; elSonuc.className = 'kosu-sonuc';
    requestAnimationFrame(dongu);
  }

  // ---- engeller ----
  var TIPLER = [
    { ad: 'fincan', w: 46, h: 34 },
    { ad: 'burger', w: 52, h: 46 },
    { ad: 'bardak', w: 32, h: 74 },
    { ad: 'kruvasan', w: 58, h: 32 },
    { ad: 'kahveci', w: 44, h: 62 }
  ];
  function engelEkle() {
    var t = TIPLER[Math.floor(Math.random() * TIPLER.length)];
    var x = W + 40;
    engeller.push({ ad: t.ad, x: x, y: YER - t.h, w: t.w, h: t.h });
    // arada ikili engel
    if (sure > 25 && Math.random() < 0.25) {
      var t2 = TIPLER[Math.floor(Math.random() * 3)];
      engeller.push({ ad: t2.ad, x: x + t.w + 70 + Math.random() * 30, y: YER - t2.h, w: t2.w, h: t2.h });
    }
    // kahve çekirdeği ödülü engelin üstünde
    if (Math.random() < 0.7) {
      var oy = YER - t.h - 70 - Math.random() * 40;
      odul.push({ x: x + t.w / 2 - 10, y: oy, r: 11, alindi: false });
    }
  }

  // ---- çizimler ----
  function rrect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  }

  function ciz_oyuncu() {
    var o = oyuncu, x = o.x, y = o.y;
    var adim = Math.sin(mesafe / 14);
    // bacaklar
    ctx.fillStyle = NAVY;
    if (o.yerde && durum === 'kosuyor') {
      ctx.fillRect(x + 9, y + o.h - 2, 9, 6 + adim * 5);
      ctx.fillRect(x + 26, y + o.h - 2, 9, 6 - adim * 5);
    } else {
      ctx.fillRect(x + 8, y + o.h - 2, 9, 8); ctx.fillRect(x + 27, y + o.h - 6, 9, 8);
    }
    // gövde: G logosu
    ctx.fillStyle = MAVI; rrect(x, y, o.w, o.h - 2, 12); ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = '800 30px system-ui, -apple-system, Segoe UI, sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('G', x + o.w / 2, y + o.h / 2 + 1);
    // gözler
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x + 31, y + 11, 4, 0, 7); ctx.fill();
    ctx.fillStyle = NAVY; ctx.beginPath(); ctx.arc(x + 32.5, y + 11, 2, 0, 7); ctx.fill();
  }

  function ciz_engel(e) {
    var x = e.x, y = e.y, w = e.w, h = e.h;
    if (e.ad === 'fincan') {
      ctx.fillStyle = '#fff'; rrect(x + 4, y, w - 14, h - 8, 8); ctx.fill();
      ctx.strokeStyle = NAVY; ctx.lineWidth = 3; ctx.stroke();
      ctx.beginPath(); ctx.arc(x + w - 8, y + 12, 8, -1.4, 1.4); ctx.stroke();      // kulp
      ctx.fillStyle = '#6B3F1D'; ctx.fillRect(x + 8, y + 5, w - 22, 6);              // kahve
      ctx.fillStyle = CREMA; rrect(x, y + h - 8, w - 2, 8, 4); ctx.fill();           // tabak
    } else if (e.ad === 'burger') {
      ctx.fillStyle = '#E8A04A'; rrect(x, y, w, 18, 12); ctx.fill();                  // üst ekmek
      ctx.fillStyle = '#fff'; ctx.fillRect(x + 12, y + 5, 3, 3); ctx.fillRect(x + 28, y + 8, 3, 3);
      ctx.fillStyle = '#4FB04F'; ctx.fillRect(x - 2, y + 18, w + 4, 6);               // marul
      ctx.fillStyle = '#7A3E1D'; rrect(x, y + 24, w, 10, 4); ctx.fill();              // köfte
      ctx.fillStyle = '#E8A04A'; rrect(x, y + 34, w, h - 34, 6); ctx.fill();          // alt ekmek
    } else if (e.ad === 'bardak') {
      ctx.fillStyle = '#fff'; ctx.beginPath();
      ctx.moveTo(x, y + 8); ctx.lineTo(x + w, y + 8); ctx.lineTo(x + w - 5, y + h); ctx.lineTo(x + 5, y + h); ctx.closePath(); ctx.fill();
      ctx.fillStyle = CREMA; ctx.fillRect(x + 3, y + 30, w - 6, 20);                   // kol bandı
      ctx.fillStyle = NAVY; rrect(x - 3, y, w + 6, 10, 4); ctx.fill();                 // kapak
    } else if (e.ad === 'kruvasan') {
      ctx.fillStyle = '#D9923C';
      ctx.beginPath(); ctx.ellipse(x + w / 2, y + h / 2 + 2, w / 2, h / 2, 0, 0, 7); ctx.fill();
      ctx.strokeStyle = '#A8681F'; ctx.lineWidth = 3;
      for (var i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(x + i * w / 4, y + 4); ctx.lineTo(x + i * w / 4 - 4, y + h - 2); ctx.stroke(); }
    } else {   // kahveci: espresso makinesi
      ctx.fillStyle = '#9AA3B2'; rrect(x, y, w, h, 6); ctx.fill();
      ctx.fillStyle = NAVY; ctx.fillRect(x + 6, y + 8, w - 12, 12);
      ctx.fillStyle = '#E0554B'; ctx.beginPath(); ctx.arc(x + w - 11, y + 36, 4, 0, 7); ctx.fill();
      ctx.fillStyle = NAVY; ctx.fillRect(x + 10, y + 40, 8, 14);
    }
  }

  function ciz_odul(o) {
    ctx.save(); ctx.translate(o.x + o.r, o.y + o.r); ctx.rotate(-0.5);
    ctx.fillStyle = '#6B3F1D'; ctx.beginPath(); ctx.ellipse(0, 0, o.r * 0.75, o.r, 0, 0, 7); ctx.fill();
    ctx.strokeStyle = CREMA; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, -o.r + 2); ctx.quadraticCurveTo(4, 0, 0, o.r - 2); ctx.stroke();
    ctx.restore();
  }

  function ciz_zemin() {
    // gökyüzü
    var g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#FFF1CF'); g.addColorStop(1, '#FFE0A0');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    // bulutlar
    ctx.fillStyle = 'rgba(255,255,255,.7)';
    bulutlar.forEach(function (b) {
      ctx.beginPath(); ctx.ellipse(b.x, b.y, 38 * b.s, 14 * b.s, 0, 0, 7); ctx.ellipse(b.x + 22 * b.s, b.y + 4, 26 * b.s, 11 * b.s, 0, 0, 7); ctx.fill();
    });
    // uzak siluet (binalar)
    ctx.fillStyle = 'rgba(11,15,46,.08)';
    var kay = -(mesafe * 0.15) % 160;
    for (var i = -1; i < 7; i++) {
      var bx = kay + i * 160, bh = 70 + ((i * 37) % 5 + 5) % 5 * 14;
      ctx.fillRect(bx, YER - bh, 110, bh);
    }
    // yer
    ctx.fillStyle = NAVY; ctx.fillRect(0, YER + 8, W, H - YER);
    ctx.fillStyle = CREMA; ctx.fillRect(0, YER + 8, W, 5);
    ctx.fillStyle = 'rgba(255,255,255,.18)';
    var k2 = -(mesafe * 1.0) % 60;
    for (var j = -1; j < 15; j++) ctx.fillRect(k2 + j * 60, YER + 30, 28, 4);
  }

  function ciz_arayuz() {
    ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    ctx.fillStyle = NAVY; ctx.font = '700 22px system-ui, sans-serif';
    ctx.fillText(String(skor()), 18, 14);
    ctx.font = '600 13px system-ui, sans-serif'; ctx.fillStyle = 'rgba(11,15,46,.6)';
    ctx.fillText('EN İYİ ' + Math.max(enSkor, skor()), 18, 42);
    ctx.textAlign = 'right';
    ctx.fillText('Hız x' + (hiz / 300).toFixed(1), W - 18, 18);
  }

  function ciz_ortaYazi(b, a) {
    ctx.fillStyle = 'rgba(255,246,226,.82)'; ctx.fillRect(0, 0, W, H);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = NAVY; ctx.font = '800 38px system-ui, sans-serif'; ctx.fillText(b, W / 2, H / 2 - 22);
    ctx.font = '500 17px system-ui, sans-serif'; ctx.fillStyle = 'rgba(11,15,46,.7)'; ctx.fillText(a, W / 2, H / 2 + 22);
  }

  function carpisma(a, b) {
    var m = 7;     // affedici pay
    return a.x + m < b.x + b.w - m && a.x + a.w - m > b.x + m && a.y + m < b.y + b.h && a.y + a.h > b.y + m;
  }

  function guncelle(dt) {
    sure += dt;
    hiz = Math.min(300 + sure * 9, 760);
    mesafe += hiz * dt;
    // oyuncu
    oyuncu.vy += 2300 * dt;
    oyuncu.y += oyuncu.vy * dt;
    if (oyuncu.y >= YER - oyuncu.h) { oyuncu.y = YER - oyuncu.h; oyuncu.vy = 0; oyuncu.yerde = true; oyuncu.ziplama = 0; }
    // engel üretimi (zaman bazlı, hız arttıkça aralık mesafesi büyür)
    sonrakiEngel -= dt;
    if (sonrakiEngel <= 0) {
      engelEkle();
      sonrakiEngel = Math.max(0.75, 1.5 - sure * 0.012) + Math.random() * 0.7;
    }
    engeller.forEach(function (e) { e.x -= hiz * dt; });
    odul.forEach(function (o) { o.x -= hiz * dt; });
    bulutlar.forEach(function (b) { b.x -= hiz * dt * 0.08 * b.s; if (b.x < -80) b.x = W + 60; });
    engeller = engeller.filter(function (e) { return e.x + e.w > -20; });
    odul = odul.filter(function (o) { return o.x > -30 && !o.alindi; });
    // ödül
    odul.forEach(function (o) {
      var dx = o.x + o.r - (oyuncu.x + oyuncu.w / 2), dy = o.y + o.r - (oyuncu.y + oyuncu.h / 2);
      if (dx * dx + dy * dy < 34 * 34) { o.alindi = true; puanEk += 25; }
    });
    // çarpışma
    for (var i = 0; i < engeller.length; i++) {
      if (carpisma(oyuncu, engeller[i])) { bitir(); return; }
    }
  }

  function bitir() {
    durum = 'bitti'; bitisZamani = performance.now();
    var s = skor();
    var yeniRekor = s > enSkor;
    if (yeniRekor) enSkor = s;
    if (elSkor) elSkor.textContent = String(s);
    if (elEn) elEn.textContent = String(enSkor);
    elSonuc.className = 'kosu-sonuc';
    elSonuc.textContent = yeniRekor && s > 0 ? 'Yeni kişisel rekor: ' + s + ' · kaydediliyor…' : 'Skor: ' + s + ' · kaydediliyor…';
    if (s > 0 && sure >= 3) {
      var fd = new FormData();
      fd.append('skor', s); fd.append('sure_sn', Math.floor(sure)); fd.append('csrfmiddlewaretoken', csrf);
      fetch(url, { method: 'POST', body: fd, credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j && j.ok) {
            elSonuc.className = 'kosu-sonuc ok';
            elSonuc.textContent = 'Skor: ' + s + ' kaydedildi' + (j.hafta_sira ? ' · bu hafta ' + j.hafta_sira + '. sıradasın' : '') + '.';
            var el = document.getElementById('kosu-yenile'); if (el) el.hidden = false;
          } else { elSonuc.textContent = 'Skor: ' + s + ' (kaydedilemedi, ' + ((j && j.mesaj) || 'tekrar dene') + ')'; }
        })
        .catch(function () { elSonuc.textContent = 'Skor: ' + s + ' (bağlantı hatası, kaydedilemedi)'; });
    } else {
      elSonuc.textContent = 'Skor: ' + s;
    }
  }

  function dongu(t) {
    if (durum !== 'kosuyor') { ciz(); return; }
    var dt = Math.min((t - sonKare) / 1000, 0.05); sonKare = t;
    guncelle(dt);
    ciz();
    if (durum === 'kosuyor') requestAnimationFrame(dongu);
  }

  function ciz() {
    ciz_zemin();
    odul.forEach(ciz_odul);
    engeller.forEach(ciz_engel);
    ciz_oyuncu();
    ciz_arayuz();
    if (durum === 'hazir') ciz_ortaYazi('Geek Koşusu', 'Başlamak için dokun veya Boşluk tuşuna bas');
    if (durum === 'bitti') ciz_ortaYazi('Oyun bitti · ' + skor(), 'Tekrar denemek için dokun veya Boşluk tuşuna bas');
  }

  // ---- girdiler ----
  window.addEventListener('keydown', function (e) {
    if (e.code === 'Space' || e.code === 'ArrowUp' || e.code === 'KeyW') {
      if (document.activeElement && /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
      e.preventDefault(); if (!e.repeat) zipla();
    }
  });
  window.addEventListener('keyup', function (e) {
    if (e.code === 'Space' || e.code === 'ArrowUp' || e.code === 'KeyW') biraktim();
  });
  cv.addEventListener('pointerdown', function (e) { e.preventDefault(); zipla(); });
  cv.addEventListener('pointerup', biraktim);
  cv.addEventListener('pointercancel', biraktim);
  document.addEventListener('visibilitychange', function () {
    if (document.hidden && durum === 'kosuyor') { durum = 'bitti'; bitisZamani = performance.now(); bitir(); ciz(); }
  });

  sifirla();
  ciz();
})();
