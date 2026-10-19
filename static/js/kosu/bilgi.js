/* Geek Bilgi Yarışması — 1000'den fazla soruluk genel kültür yarışması (Geek uyarlaması).
   Saf DOM; 3B sahneye ihtiyaç duymaz. Oyun salonuna (#kosu-oyun) üçüncü mod olarak bağlanır.
   Kurallar: sorular kolaydan zora gider, İLK YANLIŞ cevapta oyun biter ve doğru cevabın hikâyesi gösterilir.
   Puan: zorluğa göre taban + hız bonusu, doğru sayısına göre çarpan (en çok x2). Sunucu sınırı: soru başına 100–1800.
   Soru dosyaları (sorular_*.js) GeekKosu.sorular dizisine { k, ad, q } ekler; q satırları:
   zorluk|soru|DOĞRU|yanlış|yanlış|yanlış|açıklama */
(function (g) {
  'use strict';
  var GK = g.GeekKosu = g.GeekKosu || {};

  var SURE = 25;                              // soru başına saniye
  var EK_SURE = 10;                           // "+10 sn" jokeri
  var TABAN = [100, 150, 250, 400, 600];      // zorluk 1..5 taban puanı
  var HIZ_ORAN = 0.5;                         // en çok taban x 0.5 hız bonusu
  var CARPAN_ADIM = 0.1, CARPAN_TAVAN = 10;   // her doğruda +%10, en çok x2
  var MIN_PUAN = 100;                         // sunucudaki BILGI_SORU_MIN_PUAN ile aynı
  var MAX_PUAN = 1800;                        // sunucudaki BILGI_SORU_MAX_PUAN ile aynı
  var HARF = ['A', 'B', 'C', 'D'];
  var KAT_RENK = { kahve: '#d49a5a', turkiye: '#ec5b5b', tarih: '#d6b866', bilim: '#4cc3f0', cografya: '#44c685', sanat: '#cc72ea', spor: '#ff9447', teknoloji: '#6f8cff', yemek: '#f5ca3b', doga: '#7bd65f', genel: '#a7b4d4' };
  var KAT_SIRA = ['kahve', 'turkiye', 'tarih', 'bilim', 'cografya', 'sanat', 'spor', 'teknoloji', 'yemek', 'doga', 'genel'];

  /* ---------- veri ---------- */
  var BANKA = null, KATLAR = null;
  function hash(s) { var h = 5381; for (var i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; return h.toString(36); }
  function bankaKur() {
    BANKA = []; KATLAR = {};
    (GK.sorular || []).forEach(function (c) {
      KATLAR[c.k] = { k: c.k, ad: c.ad, say: 0 };
      String(c.q).split('\n').forEach(function (satir) {
        satir = satir.trim(); if (!satir) return;
        var a = satir.split('|'); if (a.length !== 7) return;
        var z = parseInt(a[0], 10); if (!(z >= 1 && z <= 5)) return;
        BANKA.push({ id: hash(a[1]), k: c.k, z: z, s: a[1], d: a[2], y: [a[3], a[4], a[5]], a: a[6] });
        KATLAR[c.k].say++;
      });
    });
    return BANKA;
  }
  function banka() { return BANKA || bankaKur(); }
  function kategoriler() { banka(); return KAT_SIRA.filter(function (k) { return KATLAR[k]; }).map(function (k) { return KATLAR[k]; }).concat(Object.keys(KATLAR).filter(function (k) { return KAT_SIRA.indexOf(k) < 0; }).map(function (k) { return KATLAR[k]; })); }

  function karistir(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function puanYaz(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }
  function sureYaz(sn) { return Math.floor(sn / 60) + ':' + ('0' + (sn % 60)).slice(-2); }

  /* ---------- kurallar ---------- */
  function zorlukTier(n) { return n < 3 ? 1 : n < 7 ? 2 : n < 12 ? 3 : n < 18 ? 4 : 5; }
  function carpan(dogru) { return 1 + Math.min(dogru, CARPAN_TAVAN) * CARPAN_ADIM; }
  // z: zorluk 1..5, kalan: kalan saniye, toplam: o sorunun toplam süresi, dogru: bu soruya kadar doğru sayısı
  function puanHesapla(z, kalan, toplam, dogru) {
    var taban = TABAN[z - 1], oran = Math.max(0, Math.min(1, kalan / (toplam || SURE)));
    var hiz = Math.floor(taban * HIZ_ORAN * oran / 5) * 5;
    return Math.max(MIN_PUAN, Math.min(MAX_PUAN, Math.round((taban + hiz) * carpan(dogru))));
  }
  function unvan(dogru) { return dogru < 3 ? 'Isınma turu' : dogru < 8 ? 'Fena değil' : dogru < 15 ? 'Bilgili çıktın' : dogru < 25 ? 'Bilgi ustası' : 'Geek Profesör'; }

  /* ---------- görülen sorular (tarayıcıda, yalnızca öncelik için) ---------- */
  function gorulenOku() { try { var v = JSON.parse(localStorage.getItem('bilgi_gorulen') || '[]'); var o = {}; (Array.isArray(v) ? v : []).forEach(function (x) { o[x] = 1; }); return o; } catch (e) { return {}; } }
  function gorulenYaz(o) { try { var k = Object.keys(o); if (k.length > 2500) k = k.slice(k.length - 2500); localStorage.setItem('bilgi_gorulen', JSON.stringify(k)); } catch (e) {} }

  // Sıradaki soruyu seç: istenen zorluk, kategori filtresi, bu oyunda kullanılmamış, tercihen daha önce görülmemiş.
  function soruSec(n, kat, kullanilan, gorulen, sonKat, tierZorla) {
    var tier = tierZorla || zorlukTier(n), tum = banka();
    var havuz = tum.filter(function (q) { return (!kat || q.k === kat) && !kullanilan[q.id]; });
    if (!havuz.length) return null;
    var aday = [], fark = 0;
    while (!aday.length && fark < 5) {
      aday = havuz.filter(function (q) { return Math.abs(q.z - tier) === fark; });
      if (!aday.length && fark) aday = havuz.filter(function (q) { return q.z === tier - fark || q.z === tier + fark; });
      fark++;
    }
    if (!aday.length) aday = havuz;
    var yeni = aday.filter(function (q) { return !gorulen[q.id]; });
    if (yeni.length) aday = yeni;
    if (!kat && sonKat) { var farkli = aday.filter(function (q) { return q.k !== sonKat; }); if (farkli.length) aday = farkli; }
    return aday[Math.floor(Math.random() * aday.length)];
  }
  function sorulastir(q) { // şıkları karıştırıp oyun nesnesi üret
    var siklar = karistir([{ t: q.d, d: true }].concat(q.y.map(function (t) { return { t: t, d: false }; })));
    return { id: q.id, k: q.k, z: q.z, s: q.s, a: q.a, siklar: siklar };
  }

  function el(tag, cls, ozellik, cocuk) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (ozellik) for (var k in ozellik) { if (k === 'metin') e.textContent = ozellik[k]; else if (k === 'html') e.innerHTML = ozellik[k]; else e.setAttribute(k, ozellik[k]); }
    if (cocuk) cocuk.forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }

  /* ---------- arayüz ---------- */
  function kur(kok, ayar) {
    ayar = ayar || {};
    var olay = ayar.olay || function () {}, ses = ayar.ses || function () {};
    var katman = el('div', 'go-bilgi', { id: 'kosu-bilgi', hidden: '', role: 'dialog', 'aria-label': 'Geek Bilgi Yarışması' });
    kok.appendChild(katman);

    var D = null, ekranAd = '', kat = '', siraMetin = '', siraEl = null;
    /* Geek Motor: her ekran (giris/soru/bitis) bir sahnedir; gecikmeler ve tween'ler sahneye bağlıdır, sahne değişince temizlenir */
    var M = GK.motor, yigin = null, rafId = 0, sonT = 0;
    if (M && M.SahneYigini) {
      yigin = new M.SahneYigini();
      yigin.tanimla('giris', {}).tanimla('soru', { onAdim: function (s, dt) { geriSayim(dt); } }).tanimla('bitis', {});
    }
    function sahneGec(ad) { if (yigin) yigin.replace(ad, null, true); }
    function surucu(t) {
      if (katman.hidden) { rafId = 0; return; }
      rafId = requestAnimationFrame(surucu);
      var dt = Math.min((t - (sonT || t)) / 1000, 0.1); sonT = t;
      if (yigin) yigin.adim(dt);
    }
    function surucuBaslat() { if (!yigin || rafId) return; sonT = 0; rafId = requestAnimationFrame(surucu); }
    try { kat = localStorage.getItem('bilgi_kat') || ''; } catch (e) {}

    function tmo(f, ms) { var s = yigin && yigin.mevcut(); if (s) return s.gecikme(ms / 1000, f); return setTimeout(f, ms); }
    function temizle() {
      katman.textContent = ''; siraEl = null;
      var s = yigin && yigin.mevcut(); if (s) { s.gecikmeleriTemizle(); s.tween.hepsiniKaldir(); }
    }
    function geriSayim(dt) {
      if (!D || ekranAd !== 'soru' || D.kilit || !D.ui) return;
      var ui = D.ui; D.gecen += dt; D.kalan = Math.max(0, D.toplam - D.gecen);
      ui.halkaIleri.style.strokeDashoffset = (ui.C * (1 - D.kalan / D.toplam)).toFixed(2);
      ui.halkaYazi.textContent = String(Math.ceil(D.kalan));
      var az = D.kalan <= 8; ui.halka.classList.toggle('az', az);
      if (az && Math.ceil(D.kalan) !== D.sonTik) { D.sonTik = Math.ceil(D.kalan); ses('tik'); }
      if (D.kalan <= 0) cevapla(-1);
    }
    function buton(yazi, tur, f) { var b = el('button', 'go-buton ' + (tur || ''), { type: 'button', metin: yazi }); b.addEventListener('click', f); return b; }
    function katRenk(k) { return KAT_RENK[k] || '#a7b4d4'; }
    function katAd(k) { banka(); return KATLAR[k] ? KATLAR[k].ad : k; }

    /* --- giriş --- */
    function girisGoster() {
      temizle(); ekranAd = 'giris'; sahneGec('giris'); D = null;
      var tum = banka(), toplam = tum.length, gorulen = Object.keys(gorulenOku()).length;
      if (!toplam) {
        katman.appendChild(el('div', 'go-bilgi-kutu go-bilgi-giris', null, [
          el('h1', null, { html: 'Geek <em>Bilgi</em> Yarışması' }),
          el('p', 'go-alt-yazi', { metin: 'Soru bankası yüklenemedi. Sayfayı yenileyip tekrar dene.' }),
          buton('Ana menü', 'ikincil', function () { olay('mil_menu'); })
        ]));
        return;
      }
      var kats = kategoriler();
      if (kat && !KATLAR[kat]) kat = '';
      var chipler = el('div', 'go-bilgi-kategoriler', { role: 'radiogroup', 'aria-label': 'Kategori' });
      function chipEkle(k, yazi, say) {
        var c = el('button', 'go-bilgi-chip' + (kat === k ? ' on' : ''), { type: 'button', role: 'radio', 'aria-checked': kat === k ? 'true' : 'false', 'data-k': k }, [el('i'), el('span', null, { metin: yazi }), el('em', null, { metin: String(say) })]);
        c.style.setProperty('--kat', k ? katRenk(k) : '#ffcf0b');
        c.addEventListener('click', function () {
          kat = k; try { localStorage.setItem('bilgi_kat', k); } catch (e) {}
          [].forEach.call(chipler.children, function (x) { var on = x === c; x.classList.toggle('on', on); x.setAttribute('aria-checked', on ? 'true' : 'false'); });
          not.textContent = notYazi();
        });
        chipler.appendChild(c);
      }
      chipEkle('', 'Karışık', toplam);
      kats.forEach(function (c) { chipEkle(c.k, c.ad, c.say); });
      function notYazi() { return kat ? 'Antrenman: ' + katAd(kat) + ' soruları. Puanın sıralamaya yazılmaz.' : 'Karışık yarışma: puanın Oyun Salonu sıralamasına yazılır.'; }
      var not = el('p', 'go-bilgi-not', { metin: notYazi() });

      var kutu = el('div', 'go-bilgi-kutu go-bilgi-giris', null, [
        el('div', 'go-bilgi-ustsatir', null, [
          ayar.logo ? el('img', 'go-bilgi-logo', { src: ayar.logo, alt: 'Geek', height: 36 }) : null,
          buton('‹ Geri dön', 'ikincil go-bilgi-geri', function () { olay('mil_menu'); })
        ]),
        el('h1', null, { html: 'Geek <em>Bilgi</em> Yarışması' }),
        el('p', 'go-bilgi-sayi', { html: '<b>' + puanYaz(toplam) + '</b> soru · <b>' + kats.length + '</b> kategori · sorular kolaydan zora' }),
        el('ul', 'go-bilgi-kurallar', null, [
          el('li', null, { html: '<b>İlk yanlışta oyun biter.</b> Doğru cevabın hikâyesini birlikte okuruz.' }),
          el('li', null, { html: 'Her soruda <b>' + SURE + ' saniye</b> var. Hızlı cevap bonus, art arda doğrular çarpan kazandırır (en çok <b>x2</b>).' }),
          el('li', null, { html: '<b>3 joker:</b> 50:50, pas ve +' + EK_SURE + ' sn. Her biri bir kez.' }),
          el('li', null, { html: 'Klavye: <b>A B C D</b> ya da <b>1–4</b> ile cevapla, <b>Enter</b> ile devam et.' })
        ]),
        el('p', 'go-bilgi-baslik-kucuk', { metin: 'Kategori seç' }),
        chipler, not,
        el('p', 'go-bilgi-gorulen', { metin: 'Gördüğün soru: ' + Math.min(gorulen, toplam) + ' / ' + toplam + (gorulen < toplam ? ' · yeni sorular öncelikli gelir' : ' · hepsini gördün, tekrar başlıyoruz') }),
        el('div', 'go-bilgi-aksiyon', null, [buton('Yarışmaya başla', 'buyuk', basla)])
      ]);
      katman.appendChild(kutu);
    }

    /* --- oyun --- */
    function basla() {
      if (!banka().length) return;
      var gor = gorulenOku();
      var say = banka().filter(function (q) { return !kat || q.k === kat; });
      if (say.length && say.every(function (q) { return gor[q.id]; })) { say.forEach(function (q) { delete gor[q.id]; }); gorulenYaz(gor); gor = gorulenOku(); }
      D = { kat: kat, sayilan: kat === '', kullanilan: {}, gorulen: gor, n: 0, dogru: 0, puan: 0, enCarpan: 1, joker: { yarim: false, pas: false, sure: false }, t0: Date.now(), sonKat: '', bitti: false, kilit: false, q: null, yanlis: null };
      ses('tik');
      sonrakiSoru();
    }
    function sonrakiSoru(tierZorla) {
      var q = soruSec(D.n, D.kat, D.kullanilan, D.gorulen, D.sonKat, tierZorla);
      if (!q) { bitir('bitti'); return; }
      D.kullanilan[q.id] = 1; D.gorulen[q.id] = 1; gorulenYaz(D.gorulen); D.sonKat = q.k;
      D.q = sorulastir(q); soruGoster();
    }

    function soruGoster() {
      ekranAd = 'soru'; sahneGec('soru'); temizle();
      var q = D.q;
      D.kilit = false; D.elenen = [false, false, false, false]; D.secili = -1; D.toplam = SURE; D.kalan = SURE; D.sonTik = 99;

      var puanEl = el('b', 'go-bilgi-puan', { metin: puanYaz(D.puan) });
      var carpanEl = el('span', 'go-bilgi-carpan', { metin: 'x' + carpan(D.dogru).toFixed(1).replace('.', ',') });
      var ust = el('div', 'go-bilgi-ust', null, [
        buton('‹ Bırak', 'ikincil go-bilgi-geri', function () { biraktaOnay(this); }),
        el('div', 'go-bilgi-skor', null, [puanEl, carpanEl]),
        el('div', 'go-bilgi-sayac', { 'aria-label': 'Doğru sayısı' }, [el('b', null, { metin: String(D.dogru) }), el('span', null, { metin: 'doğru' })])
      ]);

      var halka = el('div', 'go-bilgi-halka', { role: 'timer', 'aria-label': 'Kalan süre' }, [el('svg', null), el('b', null, { metin: String(SURE) })]);
      halka.firstChild.outerHTML = '<svg viewBox="0 0 44 44" aria-hidden="true"><circle class="iz" cx="22" cy="22" r="19"/><circle class="ilerle" cx="22" cy="22" r="19"/></svg>';
      var halkaIleri = halka.querySelector('.ilerle'), halkaYazi = halka.querySelector('b');
      var C = 2 * Math.PI * 19; halkaIleri.style.strokeDasharray = C.toFixed(2); halkaIleri.style.strokeDashoffset = '0';

      var noktalar = el('span', 'go-bilgi-zorluk', { 'aria-label': 'Zorluk ' + q.z + '/5', title: 'Zorluk ' + q.z + '/5' });
      for (var i = 1; i <= 5; i++) noktalar.appendChild(el('i', i <= q.z ? 'on' : ''));
      var katRozet = el('span', 'go-bilgi-kat', null, [el('i'), el('span', null, { metin: katAd(q.k) })]);
      katman.style.setProperty('--kat', katRenk(q.k));

      var kart = el('div', 'go-bilgi-kart', null, [
        el('div', 'go-bilgi-kart-ust', null, [katRozet, noktalar, el('span', 'go-bilgi-no', { metin: 'Soru ' + (D.n + 1) })]),
        el('p', 'go-bilgi-soru', { metin: q.s, 'aria-live': 'polite' })
      ]);

      var siklar = el('div', 'go-bilgi-siklar', { role: 'group', 'aria-label': 'Şıklar' });
      var sBtn = q.siklar.map(function (s, i) {
        var b = el('button', 'go-bilgi-sik', { type: 'button', 'data-i': i }, [el('b', null, { metin: HARF[i] }), el('span', null, { metin: s.t })]);
        b.addEventListener('click', function () { cevapla(i); });
        siklar.appendChild(b); return b;
      });

      var jokerSatiri = el('div', 'go-bilgi-jokerler');
      var jDef = [['yarim', '50:50', 'İki yanlış şıkkı ele'], ['pas', 'Pas', 'Soruyu geç, puan almadan yenisine bak'], ['sure', '+' + EK_SURE + ' sn', EK_SURE + ' saniye ek süre']];
      var jBtn = {};
      jDef.forEach(function (j) {
        var b = el('button', 'go-bilgi-joker', { type: 'button', title: j[2], 'aria-label': j[2], metin: j[1] });
        if (D.joker[j[0]]) { b.disabled = true; b.classList.add('kullanildi'); }
        b.addEventListener('click', function () { jokerKullan(j[0]); });
        jBtn[j[0]] = b; jokerSatiri.appendChild(b);
      });

      var aciklama = el('div', 'go-bilgi-aciklama', { hidden: '', 'aria-live': 'polite' });
      var kutu = el('div', 'go-bilgi-kutu go-bilgi-oyun', null, [ust, el('div', 'go-bilgi-sure-satir', null, [halka, kart]), siklar, jokerSatiri, aciklama]);
      katman.appendChild(kutu);
      katman.scrollTop = 0;

      D.ui = { sBtn: sBtn, jBtn: jBtn, halkaIleri: halkaIleri, halkaYazi: halkaYazi, halka: halka, C: C, aciklama: aciklama, puanEl: puanEl, kart: kart, jokerSatiri: jokerSatiri };
      D.gecen = 0;
    }

    function biraktaOnay(b) {
      if (D && D.kilit) return;
      if (!b.dataset.emin) { b.dataset.emin = '1'; b.textContent = 'Emin misin?'; tmo(function () { delete b.dataset.emin; b.textContent = '‹ Bırak'; }, 3000); return; }
      if (D.dogru > 0) bitir('birak'); else { kapatDahili(); olay('mil_menu'); }
    }

    function jokerKullan(ad) {
      if (!D || D.kilit || D.joker[ad]) return;
      var q = D.q, ui = D.ui;
      D.joker[ad] = true; ui.jBtn[ad].disabled = true; ui.jBtn[ad].classList.add('kullanildi'); ses('guc');
      if (ad === 'yarim') {
        var yanlis = []; q.siklar.forEach(function (s, i) { if (!s.d && !D.elenen[i]) yanlis.push(i); });
        karistir(yanlis).slice(0, 2).forEach(function (i) { D.elenen[i] = true; ui.sBtn[i].disabled = true; ui.sBtn[i].classList.add('elendi'); });
      } else if (ad === 'sure') {
        D.toplam += EK_SURE; ui.halka.classList.add('ek'); tmo(function () { ui.halka.classList.remove('ek'); }, 700);
      } else { // pas: puan yok, çarpan korunur; aynı zorlukta yeni soru
        D.kilit = true; D.n = Math.max(D.n, 0);
        ui.kart.classList.add('gec');
        tmo(function () { if (D && !D.bitti) sonrakiSoruAyniZorluk(); }, 380);
      }
    }
    function sonrakiSoruAyniZorluk() { sonrakiSoru(D.q.z); }

    function cevapla(i) {
      if (!D || D.kilit || ekranAd !== 'soru') return;
      if (i >= 0 && D.elenen[i]) return;
      D.kilit = true;
      var q = D.q, ui = D.ui, dogruIdx = q.siklar.findIndex(function (s) { return s.d; });
      var sure = i < 0 ? D.toplam : D.gecen;
      var kalan = Math.max(0, D.toplam - sure);
      var dogruMu = i >= 0 && q.siklar[i].d;
      ui.sBtn.forEach(function (b) { b.disabled = true; });
      Object.keys(ui.jBtn).forEach(function (k) { ui.jBtn[k].disabled = true; });
      if (i >= 0) ui.sBtn[i].classList.add('kilitli');
      ses('tik');
      tmo(function () {
        if (!D || ekranAd !== 'soru') return;
        if (i >= 0) ui.sBtn[i].classList.remove('kilitli');
        ui.sBtn[dogruIdx].classList.add('dogru');
        if (i >= 0 && !dogruMu) ui.sBtn[i].classList.add('yanlis');
        ui.halka.classList.remove('az');
        var panel = ui.aciklama; panel.hidden = false; panel.textContent = '';
        if (dogruMu) {
          var kazan = puanHesapla(q.z, kalan, D.toplam, D.dogru);
          D.dogru++; D.puan += kazan; D.n++; D.enCarpan = Math.max(D.enCarpan, carpan(D.dogru - 1));
          ses('dogru');
          ui.puanEl.textContent = puanYaz(D.puan);
          var ucan = el('span', 'go-bilgi-ucan', { metin: '+' + puanYaz(kazan) }); ui.puanEl.parentNode.appendChild(ucan); tmo(function () { ucan.remove(); }, 1100);
          ui.kart.classList.add('dogru');
          panel.className = 'go-bilgi-aciklama dogru';
          panel.appendChild(el('div', 'go-bilgi-aciklama-baslik', null, [el('b', null, { metin: 'Doğru! +' + puanYaz(kazan) + ' puan' }), el('span', null, { metin: 'Bilgi kartı · ' + katAd(q.k) })]));
          panel.appendChild(el('p', null, { metin: q.a }));
          var ileri = buton('Sonraki soru ›', 'buyuk', function () { ileriGit(); });
          ileri.classList.add('go-bilgi-ileri'); panel.appendChild(el('div', 'go-bilgi-aksiyon', null, [ileri]));
          D.ileri = ileri; ileri.focus({ preventScroll: true });
          panel.scrollIntoView && panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        } else {
          ses('yanlis');
          D.yanlis = { q: q, secilen: i >= 0 ? q.siklar[i].t : null, sure: i < 0 };
          ui.kart.classList.add('yanlis');
          panel.className = 'go-bilgi-aciklama yanlis';
          panel.appendChild(el('div', 'go-bilgi-aciklama-baslik', null, [el('b', null, { metin: i < 0 ? 'Süre doldu' : 'Yanlış cevap' }), el('span', null, { metin: 'Bilgi kartı · ' + katAd(q.k) })]));
          panel.appendChild(el('p', 'go-bilgi-dogrusu', { html: 'Doğru cevap: <b></b>' }));
          panel.querySelector('.go-bilgi-dogrusu b').textContent = q.siklar[dogruIdx].t;
          panel.appendChild(el('p', null, { metin: q.a }));
          var son = buton('Sonucu gör ›', 'buyuk', function () { bitir(i < 0 ? 'sure' : 'yanlis'); });
          son.classList.add('go-bilgi-ileri'); panel.appendChild(el('div', 'go-bilgi-aksiyon', null, [son]));
          D.ileri = son; son.focus({ preventScroll: true });
          panel.scrollIntoView && panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
      }, 650);
    }
    function ileriGit() { if (!D || D.bitti || ekranAd !== 'soru') return; D.ileri = null; sonrakiSoru(); }

    /* --- bitiş --- */
    function bitir(neden) {
      if (!D || D.bitti) return;
      D.bitti = true; ekranAd = 'bitis'; sahneGec('bitis');
      var sure = Math.max(0, Math.round((Date.now() - D.t0) / 1000));
      var sonuc = { skor: D.puan, sure: sure, dogru: D.dogru, neden: neden, sayilir: D.sayilan };
      var bas = { yanlis: 'Oyun bitti', sure: 'Süre doldu', birak: 'Yarışmayı bıraktın', bitti: 'Bütün soruları bitirdin!' }[neden] || 'Oyun bitti';
      temizle();
      siraEl = el('p', 'go-bilgi-sira', { 'aria-live': 'polite', metin: D.sayilan ? '' : 'Antrenman modu: puan sıralamaya yazılmadı.' });
      var puanEl = el('div', 'go-bilgi-buyuk-puan', { metin: '0' });
      var kutu = el('div', 'go-bilgi-kutu go-bilgi-bitis', null, [
        el('h2', null, { metin: bas }),
        el('p', 'go-bilgi-unvan', { metin: unvan(D.dogru) }),
        puanEl,
        el('p', 'go-alt-yazi', { metin: 'puan' }),
        el('div', 'go-bilgi-istat', null, [
          el('div', null, null, [el('b', null, { metin: String(D.dogru) }), el('span', null, { metin: 'doğru' })]),
          el('div', null, null, [el('b', null, { metin: 'x' + carpan(D.dogru).toFixed(1).replace('.', ',') }), el('span', null, { metin: 'son çarpan' })]),
          el('div', null, null, [el('b', null, { metin: sureYaz(sure) }), el('span', null, { metin: 'süre' })])
        ]),
        D.yanlis ? yanlisKart(D.yanlis) : null,
        siraEl,
        el('div', 'go-bilgi-aksiyon', null, [buton('Tekrar oyna', 'buyuk', function () { basla(); }), buton('Kategori seç', 'ikincil', function () { girisGoster(); }), buton('Ana menü', 'ikincil', function () { olay('mil_menu'); }), buton('Panele dön', 'ikincil', function () { olay('mil_cik'); })])
      ]);
      katman.style.removeProperty('--kat');
      katman.appendChild(kutu);
      if (siraMetin) siraEl.textContent = siraMetin;
      // puan sayacı
      var hedef = D.puan, sure_ms = Math.min(1400, 300 + hedef / 4);
      if (yigin) yigin.mevcut().tween.ekle('puan', 0, hedef, sure_ms / 1000, 'easeOutCubic', function (v) { puanEl.textContent = puanYaz(Math.round(v)); });
      else puanEl.textContent = puanYaz(hedef);
      siraMetin = '';
      if (D.sayilan && D.puan > 0 && D.dogru > 0) olay('mil_bitti', sonuc);
    }
    function yanlisKart(y) {
      var d = y.q.siklar.filter(function (s) { return s.d; })[0].t;
      var k = el('div', 'go-bilgi-kacan', null, [
        el('span', 'go-bilgi-kacan-baslik', { metin: 'Kaçırdığın soru · ' + katAd(y.q.k) }),
        el('p', 'go-bilgi-kacan-soru', { metin: y.q.s }),
        el('p', 'go-bilgi-kacan-cevap', { html: (y.secilen ? 'Senin cevabın: <s></s><br>' : '') + 'Doğrusu: <b></b>' })
      ]);
      var s = k.querySelector('s'); if (s) s.textContent = y.secilen;
      k.querySelector('b').textContent = d;
      return k;
    }

    function kapatDahili() { temizle(); }

    function klavye(e) {
      if (katman.hidden) return false;
      var k = e.key, kod = e.code;
      if (ekranAd === 'soru' && D) {
        if (D.kilit) { if (D.ileri && (kod === 'Enter' || kod === 'NumpadEnter' || kod === 'Space')) { D.ileri.click(); } return true; }
        var i = -1;
        if (/^[abcd]$/i.test(k)) i = k.toLowerCase().charCodeAt(0) - 97; else if (/^[1-4]$/.test(k)) i = +k - 1;
        if (i >= 0) { cevapla(i); return true; }
        if (kod === 'Escape') { var b = katman.querySelector('.go-bilgi-geri'); if (b) b.click(); return true; }
        return true;
      }
      if (ekranAd === 'giris') { if (kod === 'Enter' || kod === 'NumpadEnter') { basla(); return true; } if (kod === 'Escape') { olay('mil_menu'); return true; } return true; }
      if (ekranAd === 'bitis') { if (kod === 'Enter' || kod === 'NumpadEnter') { basla(); return true; } if (kod === 'Escape') { olay('mil_menu'); return true; } return true; }
      return false;
    }

    return {
      katman: katman,
      ac: function () { katman.hidden = false; girisGoster(); surucuBaslat(); },
      kapat: function () {
        if (D && !D.bitti && D.sayilan && D.dogru > 0 && D.puan > 0) { D.bitti = true; olay('mil_bitti', { skor: D.puan, sure: Math.max(0, Math.round((Date.now() - D.t0) / 1000)), dogru: D.dogru, neden: 'birak', sayilir: true }); }
        kapatDahili(); katman.hidden = true; D = null; ekranAd = ''; if (yigin) yigin.temizle(); if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
      },
      aktif: function () { return !katman.hidden; },
      klavye: klavye,
      sira: function (yazi) { siraMetin = yazi || ''; if (siraEl) { siraEl.textContent = siraMetin; siraMetin = ''; } },
      durum: function () { return D ? { n: D.n, dogru: D.dogru, puan: D.puan, ekran: ekranAd, kalan: D.kalan, joker: D.joker, bitti: D.bitti } : { ekran: ekranAd }; },
      _d: function () { return D; }
    };
  }

  GK.bilgi = { kur: kur, banka: banka, kategoriler: kategoriler, soruSec: soruSec, sorulastir: sorulastir, puanHesapla: puanHesapla, zorlukTier: zorlukTier, carpan: carpan, unvan: unvan, puanYaz: puanYaz, hash: hash, SURE: SURE, TABAN: TABAN, MIN_PUAN: MIN_PUAN, MAX_PUAN: MAX_PUAN, CARPAN_TAVAN: CARPAN_TAVAN };
  if (typeof module !== 'undefined' && module.exports) module.exports = GK.bilgi;
})(typeof window !== 'undefined' ? window : globalThis);
