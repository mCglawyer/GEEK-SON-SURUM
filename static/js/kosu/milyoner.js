/* Geek Milyoner — "Kim Milyoner Olmak İster" tarzı bilgi yarışması (Geek uyarlaması).
   Saf DOM; 3B sahneye ihtiyaç duymaz. Oyun salonuna (#kosu-oyun) üçüncü mod olarak bağlanır.
   Kurallar: 15 soru, ödül merdiveni, güvenli basamaklar (5. ve 10. soru), 3 joker, soru başına süre. */
(function (g) {
  'use strict';
  var GK = g.GeekKosu = g.GeekKosu || {};

  // Ödül merdiveni: sunucudaki MILYONER_MERDIVEN ile birebir aynı olmalı.
  var MERDIVEN = [100, 200, 300, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000, 125000, 250000, 500000, 1000000];
  var GUVENLI = [4, 9];          // 1.000 ve 32.000 güvenli basamak (dizin)
  var SURE = 60;                 // soru başına saniye
  var HARF = ['A', 'B', 'C', 'D'];

  // Her seviye (3 soruluk grup) için havuz: [soru, DOĞRU, yanlış, yanlış, yanlış]
  var HAVUZ = [
    [
      ['Espresso hangi ülkeyle özdeşleşmiş bir kahvedir?', 'İtalya', 'Japonya', 'Kanada', 'Mısır'],
      ['Türk kahvesi geleneksel olarak hangi kapta pişirilir?', 'Cezve', 'Demlik', 'Semaver', 'Güveç'],
      ['İtalyancada "latte" kelimesi ne anlama gelir?', 'Süt', 'Kahve', 'Köpük', 'Şeker'],
      ['Hangisi bir kahve çeşidi değildir?', 'Simit', 'Americano', 'Mocha', 'Cortado'],
      ['Türkiye\'nin başkenti neresidir?', 'Ankara', 'İstanbul', 'İzmir', 'Bursa'],
      ['Dünyanın en büyük okyanusu hangisidir?', 'Pasifik Okyanusu', 'Atlas Okyanusu', 'Hint Okyanusu', 'Arktik Okyanusu'],
      ['Geek Panel\'de skor tablolarının ve sosyal akışın bulunduğu sayfa hangisidir?', 'Geek Crew', 'Dijital Menü', 'Vardiya Planı', 'Stok Sayımı'],
      ['Kahve çekirdekleri kavrulmadan önce hangi renktedir?', 'Yeşil', 'Mor', 'Mavi', 'Kırmızı']
    ],
    [
      ['Klasik bir cappuccino hangi üçlüden oluşur?', 'Espresso, sıcak süt, süt köpüğü', 'Espresso, sıcak su, krema', 'Filtre kahve, soğuk süt, buz', 'Espresso, çikolata, şurup'],
      ['Menengiç kahvesi hangi ilimizle özdeşleşmiştir?', 'Gaziantep', 'Rize', 'Edirne', 'Sinop'],
      ['Hangisi Gaziantep ile özdeşleşmiş bir tatlıdır?', 'Baklava', 'Tavuk göğsü', 'Kazandibi', 'Aşure'],
      ['Americano hangi ikilinin karışımıdır?', 'Espresso ve sıcak su', 'Espresso ve süt', 'Filtre kahve ve buz', 'Çay ve süt'],
      ['Dünyada en çok kahve üreten ülke hangisidir?', 'Brezilya', 'Kanada', 'İsviçre', 'Rusya'],
      ['"Barista" kelimesi dilimize hangi dilden girmiştir?', 'İtalyanca', 'Fransızca', 'İspanyolca', 'Almanca'],
      ['Kahve çekirdeği aslında neyin tohumudur?', 'Kahve kirazının (meyvesinin)', 'Bir tür fındığın', 'Bir baklagilin', 'Bir ot bitkisinin'],
      ['Türk kahvesi yanında geleneksel olarak ne ile servis edilir?', 'Lokum ve bir bardak su', 'Simit ve ayran', 'Kek ve limonata', 'Tuzlu kraker ve çay'],
      ['Bir "shot" espresso ne demektir?', 'Tek servislik espresso', 'Çift süt', 'Buzlu kahve', 'Köpüklü süt']
    ],
    [
      ['Arabica ve Robusta hangi bitkinin başlıca türleridir?', 'Kahve', 'Çay', 'Kakao', 'Tütün'],
      ['Arabica çekirdeği Robusta ile karşılaştırıldığında genellikle nasıldır?', 'Daha az kafein içerir', 'Çok daha fazla kafein içerir', 'Hiç kafein içermez', 'Her zaman daha acıdır'],
      ['"Macchiato" İtalyancada ne anlama gelir?', 'Lekeli', 'Köpüklü', 'Sıcak', 'Çift'],
      ['Türk kahvesi kültürü ve geleneği UNESCO Somut Olmayan Kültürel Miras listesine hangi yıl girdi?', '2013', '1999', '2005', '2021'],
      ['Kahve bitkisinin kırmızı meyvesine ne ad verilir?', 'Kahve kirazı', 'Kahve eriği', 'Kahve narı', 'Kahve üzümü'],
      ['Mona Lisa tablosunun ressamı kimdir?', 'Leonardo da Vinci', 'Michelangelo', 'Rembrandt', 'Picasso'],
      ['Mimar Sinan\'ın "ustalık eserim" dediği cami hangisidir?', 'Selimiye Camii', 'Süleymaniye Camii', 'Sultanahmet Camii', 'Şehzade Camii'],
      ['Flat white kahvesinin çıkış yeri olarak en çok hangi ülkeler tartışılır?', 'Avustralya ve Yeni Zelanda', 'Meksika ve Peru', 'Norveç ve İsveç', 'Hindistan ve Nepal']
    ],
    [
      ['Efsaneye göre kahveyi keşfeden çoban Kaldi hangi ülkeden kabul edilir?', 'Etiyopya', 'Brezilya', 'Kolombiya', 'Vietnam'],
      ['İstanbul\'da ilk kahvehaneler yaklaşık hangi yüzyılda açıldı?', '16. yüzyıl', '12. yüzyıl', '19. yüzyıl', '20. yüzyıl'],
      ['Espresso makinesinin ilk patenti 1884\'te hangi İtalyan şehrinde alındı?', 'Torino', 'Roma', 'Napoli', 'Palermo'],
      ['Espresso üzerindeki altın renkli köpük tabakasına ne ad verilir?', 'Crema', 'Latte art', 'Foam', 'Brûlée'],
      ['"V60" demleme aracı hangi ülkenin markasıdır?', 'Japonya', 'Almanya', 'Norveç', 'Kanada'],
      ['Cold brew (soğuk demleme) genellikle kaç saat bekletilir?', '12–24 saat', '5–10 dakika', '30 saniye', '3–4 gün'],
      ['Altının kimyasal simgesi nedir?', 'Au', 'Ag', 'Fe', 'Go'],
      ['French press yönteminde kahve nasıl demlenir?', 'Suda bekletilip (daldırma) süzülür', 'Basınçla geçirilir', 'Kâğıt filtreden damlatılır', 'Kaynatılarak pişirilir']
    ],
    [
      ['Rekor fiyatlı kahve partileriyle ün kazanan "Geisha" çeşidi hangi ülkedeki çiftliklerle öne çıktı?', 'Panama', 'Çin', 'Rusya', 'Polonya'],
      ['Robusta çekirdeği Arabica\'ya göre yaklaşık ne kadar kafein içerir?', 'Yaklaşık iki katı', 'Yaklaşık yarısı', 'Hiç içermez', 'Aynı miktar'],
      ['Kopi Luwak kahvesi hangi hayvanın sindirim sisteminden geçen çekirdeklerle yapılır?', 'Misk kedisi', 'Fil', 'Kaplan', 'Maymun'],
      ['Kahvehaneleri yasaklamasıyla bilinen Osmanlı padişahı kimdir?', 'IV. Murad', 'II. Mehmed', 'I. Ahmed', 'II. Mahmud'],
      ['İyi bir espresso çekimi yaklaşık kaç saniye sürer?', '25–30 saniye', '5 saniye', '2 dakika', '10 dakika'],
      ['Etiyopya\'daki geleneksel kahve seremonisinde kahve hangi kapta pişirilir?', 'Jebena', 'Cezve', 'Moka pot', 'Semaver'],
      ['Fransızca "demi-tasse" (küçük fincan) ifadesinin kelime anlamı nedir?', 'Yarım fincan', 'Altın fincan', 'Sıcak fincan', 'Küçük kaşık']
    ]
  ];

  function karistir(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function puanYaz(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }

  // 15 soruluk bir oyun kur: her seviyeden 3 farklı soru, şıklar karışık.
  function oyunSorulari() {
    var out = [];
    for (var t = 0; t < HAVUZ.length; t++) {
      var sec = karistir(HAVUZ[t].slice()).slice(0, 3);
      sec.forEach(function (q) {
        var siklar = karistir([{ t: q[1], d: true }, { t: q[2], d: false }, { t: q[3], d: false }, { t: q[4], d: false }]);
        out.push({ s: q[0], siklar: siklar, tier: t });
      });
    }
    return out;
  }

  // Seyirci oylaması: doğru şıka seviyeye göre ağırlık verir, yüzdeler 100'e tamamlanır.
  function seyirciOyu(soru, elenen) {
    var P = [0.88, 0.74, 0.62, 0.5, 0.4][soru.tier];
    var acik = [], i;
    for (i = 0; i < 4; i++) if (!elenen[i]) acik.push(i);
    var dogru = soru.siklar.findIndex(function (x) { return x.d; });
    var pay = {}, kalan = 100, yanlislar = acik.filter(function (k) { return k !== dogru; });
    var dp = Math.round(Math.max(0.3, Math.min(0.96, P + (Math.random() - 0.5) * 0.14)) * 100);
    if (!yanlislar.length) dp = 100;
    pay[dogru] = dp; kalan -= dp;
    var w = yanlislar.map(function () { return 0.3 + Math.random(); }), tw = w.reduce(function (a, b) { return a + b; }, 0) || 1;
    yanlislar.forEach(function (k, n) { var v = n === yanlislar.length - 1 ? kalan : Math.round(kalan * w[n] / tw); pay[k] = v; kalan -= v; });
    return pay;
  }

  function telefonCevabi(soru, elenen) {
    var A = [0.95, 0.85, 0.72, 0.6, 0.5][soru.tier];
    var acik = [], i;
    for (i = 0; i < 4; i++) if (!elenen[i]) acik.push(i);
    var dogru = soru.siklar.findIndex(function (x) { return x.d; });
    var yanlislar = acik.filter(function (k) { return k !== dogru; });
    var secim = (Math.random() < A || !yanlislar.length) ? dogru : yanlislar[Math.floor(Math.random() * yanlislar.length)];
    var giris = soru.tier <= 1 ? 'Eminim, ' : soru.tier <= 3 ? 'Bence ' : 'Pek emin değilim ama ';
    return '“' + giris + HARF[secim] + ' diyorum: ' + soru.siklar[secim].t + '.”';
  }

  function el(tag, cls, ozellik, cocuk) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (ozellik) for (var k in ozellik) { if (k === 'metin') e.textContent = ozellik[k]; else if (k === 'html') e.innerHTML = ozellik[k]; else e.setAttribute(k, ozellik[k]); }
    if (cocuk) cocuk.forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }

  function kur(kok, ayar) {
    ayar = ayar || {};
    var olay = ayar.olay || function () {}, ses = ayar.ses || function () {};
    var katman = el('div', 'go-mily', { id: 'kosu-milyoner', hidden: '', role: 'dialog', 'aria-label': 'Geek Milyoner' });
    kok.appendChild(katman);

    var D = null;       // oyun durumu
    var ekranAd = '';   // giris | soru | bitis
    var zamanci = null;

    function temizle() { katman.textContent = ''; if (zamanci) { clearInterval(zamanci); zamanci = null; } }
    function geriButon(yazi, f) { var b = el('button', 'go-buton ikincil go-mily-geri', { type: 'button', metin: '‹ ' + yazi }); b.addEventListener('click', f); return b; }
    function buton(yazi, tur, f) { var b = el('button', 'go-buton ' + (tur || ''), { type: 'button', metin: yazi }); b.addEventListener('click', f); return b; }

    function girisGoster() {
      temizle(); ekranAd = 'giris';
      var kutu = el('div', 'go-mily-kutu go-mily-giris', null, [
        ayar.logo ? el('img', 'go-mily-logo', { src: ayar.logo, alt: 'Geek', height: 40 }) : null,
        el('h1', null, { html: 'Geek <em>Milyoner</em>' }),
        el('p', 'go-alt-yazi', { metin: 'Kahve, Geek ve genel kültür: 15 soruyu bil, bir milyon puana ulaş.' }),
        el('ul', 'go-mily-kurallar', null, [
          el('li', null, { html: '<b>15 soru</b>, her soruda <b>' + SURE + ' saniye</b> süren var.' }),
          el('li', null, { html: '<b>5. soru (1.000)</b> ve <b>10. soru (32.000)</b> güvenli basamaktır; yanlış cevapta oraya düşersin.' }),
          el('li', null, { html: '<b>3 joker:</b> yarı yarıya, seyirci ve telefon. Her biri bir kez.' }),
          el('li', null, { html: 'Emin değilsen <b>Çekil</b>: bulunduğun basamağı kapar.' }),
          el('li', null, { html: 'Klavye: <b>A B C D</b> ya da <b>1–4</b> seç, <b>Enter</b> kilitle.' })
        ]),
        el('div', 'go-mily-aksiyon', null, [buton('Yarışmaya başla', 'buyuk', basla), geriButon('Geri dön', function () { olay('mil_menu'); })])
      ]);
      katman.appendChild(kutu);
    }

    function basla() {
      D = { sorular: oyunSorulari(), n: 0, joker: { yarim: false, seyirci: false, telefon: false }, elenen: [false, false, false, false], secili: -1, kilit: false, t0: Date.now(), kalan: SURE, bitti: false, oy: null, tel: null };
      ses('tik');
      soruGoster();
    }

    function guvenliOdul(n) { // n = doğru bilinen soru sayısı
      if (n >= GUVENLI[1] + 1) return MERDIVEN[GUVENLI[1]];
      if (n >= GUVENLI[0] + 1) return MERDIVEN[GUVENLI[0]];
      return 0;
    }

    function soruGoster() {
      temizle(); ekranAd = 'soru';
      var q = D.sorular[D.n];
      D.elenen = [false, false, false, false]; D.secili = -1; D.kilit = false; D.oy = null; D.tel = null; D.kalan = SURE;

      var sayac = el('div', 'go-mily-sure', { 'aria-hidden': 'true' }, [el('i')]);
      var sureYazi = el('span', 'go-mily-sure-yazi', { metin: String(SURE) });
      var jokerSatiri = el('div', 'go-mily-jokerler');
      var jDef = [['yarim', '50:50', 'Yarı yarıya: iki yanlış şıkkı eler'], ['seyirci', 'Seyirci', 'Seyirciye sor'], ['telefon', 'Telefon', 'Bir dosta telefon et']];
      var jBtn = {};
      jDef.forEach(function (j) {
        var b = el('button', 'go-mily-joker', { type: 'button', 'aria-label': j[2], title: j[2], metin: j[1] });
        if (D.joker[j[0]]) { b.disabled = true; b.classList.add('kullanildi'); }
        b.addEventListener('click', function () { jokerKullan(j[0]); });
        jBtn[j[0]] = b; jokerSatiri.appendChild(b);
      });

      var siklarKutu = el('div', 'go-mily-siklar', { role: 'group', 'aria-label': 'Şıklar' });
      var sBtn = q.siklar.map(function (s, i) {
        var b = el('button', 'go-mily-sik', { type: 'button', 'data-i': i }, [el('b', null, { metin: HARF[i] }), el('span', null, { metin: s.t }), el('em', 'go-mily-oy', { 'aria-hidden': 'true' })]);
        b.addEventListener('click', function () { sec(i); });
        siklarKutu.appendChild(b); return b;
      });

      var telBalon = el('div', 'go-mily-balon', { hidden: '', role: 'status' });
      var kilitBtn = buton('Kilitle', 'buyuk', function () { kilitle(); }); kilitBtn.disabled = true;
      var cekilBtn = buton('Çekil', 'ikincil', function () {
        if (D.kilit) return;
        if (!cekilBtn.dataset.emin) { cekilBtn.dataset.emin = '1'; cekilBtn.textContent = D.n ? 'Emin misin? ' + puanYaz(MERDIVEN[D.n - 1]) + ' ile çekil' : 'Emin misin? 0 ile çık'; setTimeout(function () { delete cekilBtn.dataset.emin; cekilBtn.textContent = 'Çekil'; }, 3500); return; }
        bitir('cekil');
      });

      // ödül merdiveni
      var merd = el('ol', 'go-mily-merdiven', { 'aria-label': 'Ödül merdiveni' });
      for (var i = MERDIVEN.length - 1; i >= 0; i--) {
        var li = el('li', null, null, [el('span', null, { metin: String(i + 1) }), el('b', null, { metin: puanYaz(MERDIVEN[i]) })]);
        if (GUVENLI.indexOf(i) >= 0) li.classList.add('guvenli');
        if (i < D.n) li.classList.add('gecti');
        if (i === D.n) li.classList.add('simdi');
        merd.appendChild(li);
      }

      var ust = el('div', 'go-mily-ust', null, [
        geriButon('Geri dön', function () { if (D && !D.kilit) olay('mil_menu'); }),
        el('div', 'go-mily-bilgi', null, [el('b', null, { metin: 'Soru ' + (D.n + 1) + '/15' }), el('span', null, { metin: puanYaz(MERDIVEN[D.n]) + ' puan' })]),
        el('button', 'go-mily-merd-ac', { type: 'button', 'aria-label': 'Ödül merdivenini göster', metin: 'Merdiven' })
      ]);
      ust.lastChild.addEventListener('click', function () { katman.classList.toggle('merdiven-acik'); });

      var sol = el('div', 'go-mily-ana', null, [
        ust,
        el('div', 'go-mily-sureSatir', null, [sayac, sureYazi]),
        jokerSatiri,
        el('p', 'go-mily-soru', { metin: q.s, 'aria-live': 'polite' }),
        siklarKutu,
        telBalon,
        el('div', 'go-mily-aksiyon', null, [kilitBtn, cekilBtn])
      ]);
      katman.appendChild(el('div', 'go-mily-kutu go-mily-oyun', null, [sol, merd]));
      katman.classList.remove('merdiven-acik');

      D.ui = { sBtn: sBtn, kilitBtn: kilitBtn, jBtn: jBtn, sayacI: sayac.firstChild, sureYazi: sureYazi, telBalon: telBalon, siklarKutu: siklarKutu, cekilBtn: cekilBtn };
      var bas = Date.now();
      sayac.firstChild.style.width = '100%';
      zamanci = setInterval(function () {
        if (D.kilit) return;
        var gecen = (Date.now() - bas) / 1000; D.kalan = Math.max(0, SURE - gecen);
        sayac.firstChild.style.width = (D.kalan / SURE * 100) + '%';
        sureYazi.textContent = String(Math.ceil(D.kalan));
        sayac.classList.toggle('az', D.kalan <= 10);
        if (D.kalan <= 10 && Math.ceil(D.kalan) !== D.sonTik) { D.sonTik = Math.ceil(D.kalan); ses('tik'); }
        if (D.kalan <= 0) bitir('sure');
      }, 200);
    }

    function sec(i) {
      if (!D || D.kilit || D.elenen[i]) return;
      D.secili = i; ses('tik');
      D.ui.sBtn.forEach(function (b, k) { b.classList.toggle('secili', k === i); b.setAttribute('aria-pressed', k === i ? 'true' : 'false'); });
      D.ui.kilitBtn.disabled = false;
      D.ui.kilitBtn.textContent = HARF[i] + ' şıkkını kilitle';
    }

    function jokerKullan(ad) {
      if (!D || D.kilit || D.joker[ad]) return;
      var q = D.sorular[D.n], ui = D.ui;
      D.joker[ad] = true; ui.jBtn[ad].disabled = true; ui.jBtn[ad].classList.add('kullanildi'); ses('guc');
      if (ad === 'yarim') {
        var yanlis = []; q.siklar.forEach(function (s, i) { if (!s.d && !D.elenen[i]) yanlis.push(i); });
        karistir(yanlis).slice(0, 2).forEach(function (i) { D.elenen[i] = true; ui.sBtn[i].disabled = true; ui.sBtn[i].classList.add('elendi'); if (D.secili === i) { D.secili = -1; ui.sBtn[i].classList.remove('secili'); ui.kilitBtn.disabled = true; ui.kilitBtn.textContent = 'Kilitle'; } });
      } else if (ad === 'seyirci') {
        var pay = seyirciOyu(q, D.elenen);
        ui.sBtn.forEach(function (b, i) {
          var o = b.querySelector('.go-mily-oy');
          if (pay[i] == null) { o.textContent = ''; return; }
          o.textContent = '%' + pay[i]; o.style.setProperty('--oy', pay[i] + '%'); b.classList.add('oylu');
        });
        ui.telBalon.hidden = false; ui.telBalon.textContent = 'Seyirci oylaması tamamlandı.';
      } else {
        ui.telBalon.hidden = false; ui.telBalon.textContent = 'Barista dostun: ' + telefonCevabi(q, D.elenen);
      }
    }

    function kilitle() {
      if (!D || D.kilit || D.secili < 0) return;
      D.kilit = true; var q = D.sorular[D.n], ui = D.ui, i = D.secili, dogruMu = q.siklar[i].d;
      ui.sBtn.forEach(function (b) { b.disabled = true; }); ui.kilitBtn.disabled = true; ui.cekilBtn.disabled = true;
      Object.keys(ui.jBtn).forEach(function (k) { ui.jBtn[k].disabled = true; });
      ui.sBtn[i].classList.add('kilitli');
      ses('tik');
      setTimeout(function () {
        if (!D || ekranAd !== 'soru') return;
        ui.sBtn[i].classList.remove('kilitli');
        q.siklar.forEach(function (s, k) { if (s.d) ui.sBtn[k].classList.add('dogru'); });
        if (!dogruMu) ui.sBtn[i].classList.add('yanlis');
        ses(dogruMu ? 'dogru' : 'yanlis');
        setTimeout(function () {
          if (!D || ekranAd !== 'soru') return;
          if (!dogruMu) { bitir('yanlis'); return; }
          D.n++;
          if (D.n >= MERDIVEN.length) bitir('kazandi'); else soruGoster();
        }, 1500);
      }, 1100);
    }

    function bitir(neden) {
      if (!D || D.bitti) return;
      D.bitti = true; ekranAd = 'bitis';
      var q = D.sorular[Math.min(D.n, D.sorular.length - 1)];
      var odul, baslik, alt;
      if (neden === 'kazandi') { odul = MERDIVEN[MERDIVEN.length - 1]; baslik = 'Tebrikler, Milyoner oldun!'; alt = 'Bütün soruları bildin.'; ses('guc'); }
      else if (neden === 'cekil') { odul = D.n ? MERDIVEN[D.n - 1] : 0; baslik = 'Çekildin'; alt = 'Bulunduğun basamağı kaptın.'; }
      else { odul = guvenliOdul(D.n); baslik = neden === 'sure' ? 'Süre doldu' : 'Yanlış cevap'; alt = ''; }
      var dogruMetin = q.siklar.filter(function (s) { return s.d; })[0].t;
      var sure = Math.max(0, Math.round((Date.now() - D.t0) / 1000));
      var sonuc = { skor: odul, sure: sure, soru: D.n, neden: neden };
      temizle();
      var siraYazi = el('p', 'go-mily-sira', { 'aria-live': 'polite' });
      var kutu = el('div', 'go-mily-kutu go-mily-bitis', null, [
        el('h2', null, { metin: baslik }),
        el('div', 'go-mily-odul', { metin: puanYaz(odul) }),
        el('p', 'go-alt-yazi', { metin: 'puan' + (alt ? ' · ' + alt : '') }),
        (neden === 'yanlis' || neden === 'sure') ? el('p', 'go-mily-dogrusu', { html: 'Doğru cevap: <b></b>' }) : null,
        el('p', 'go-alt-yazi', { metin: 'Bilinen soru: ' + D.n + '/15 · Süre: ' + Math.floor(sure / 60) + ':' + ('0' + (sure % 60)).slice(-2) }),
        siraYazi,
        el('div', 'go-mily-aksiyon', null, [buton('Tekrar oyna', 'buyuk', basla), buton('Ana menü', 'ikincil', function () { olay('mil_menu'); }), buton('Panele dön', 'ikincil', function () { olay('mil_cik'); })])
      ]);
      var b = kutu.querySelector('.go-mily-dogrusu b'); if (b) b.textContent = dogruMetin;
      katman.appendChild(kutu);
      D.siraYazi = siraYazi;
      if (odul > 0) olay('mil_bitti', sonuc);
    }

    function klavye(e) {
      if (katman.hidden) return false;
      var k = e.key, kod = e.code;
      if (ekranAd === 'soru' && D) {
        var i = -1;
        if (/^[abcd]$/i.test(k)) i = k.toLowerCase().charCodeAt(0) - 97; else if (/^[1-4]$/.test(k)) i = +k - 1;
        if (i >= 0) { sec(i); return true; }
        if (kod === 'Enter' || kod === 'NumpadEnter') { kilitle(); return true; }
        if (kod === 'Escape') { if (!D.kilit) D.ui.cekilBtn.click(); return true; }
        return true;
      }
      if (ekranAd === 'giris') { if (kod === 'Enter') { basla(); return true; } if (kod === 'Escape') { olay('mil_menu'); return true; } return true; }
      if (ekranAd === 'bitis') { if (kod === 'Enter') { basla(); return true; } if (kod === 'Escape') { olay('mil_menu'); return true; } return true; }
      return false;
    }

    return {
      katman: katman,
      ac: function () { katman.hidden = false; D = null; girisGoster(); },
      kapat: function () { temizle(); katman.hidden = true; D = null; ekranAd = ''; },
      aktif: function () { return !katman.hidden; },
      klavye: klavye,
      sira: function (yazi) { if (D && D.siraYazi) D.siraYazi.textContent = yazi || ''; },
      durum: function () { return D ? { n: D.n, ekran: ekranAd, kalan: D.kalan, joker: D.joker } : { ekran: ekranAd }; },
      // test/hata ayıklama için
      _d: function () { return D; }
    };
  }

  GK.milyoner = { kur: kur, MERDIVEN: MERDIVEN, GUVENLI: GUVENLI, HAVUZ: HAVUZ, oyunSorulari: oyunSorulari, seyirciOyu: seyirciOyu, telefonCevabi: telefonCevabi, puanYaz: puanYaz };
  if (typeof module !== 'undefined' && module.exports) module.exports = GK.milyoner;
})(typeof window !== 'undefined' ? window : globalThis);
