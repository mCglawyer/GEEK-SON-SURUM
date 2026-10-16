/* Geek Radio çekirdek oynatıcı (AzuraCast canlı yayın).
   Kalıcı kabuk içinde tek bir kez kurulur (window.GeekRadyo); sayfalar arasında gezinirken müzik kesilmez.
   Kullanıcı kendisi durdurana kadar çalar. Kabuk yoksa (eski tarayıcı) sayfa içinde yerel oynatıcı kurulur.
   Sayfalar: var R = GeekRadyoAl(cfg); R.abone(fn); R.cal(); R.durdur(); R.sesAyarla(70);
   Durum nesnesi: {caliyor, ister, baglaniyor, sarki, sanatci, art, canli, ses, not} */
(function () {
  'use strict';
  if (window.GeekRadyoOlustur) return;

  var DEPO = 'geek_radyo', SES_ANAHTAR = 'geek_radyo_ses', GECERLI_MS = 6 * 60 * 60 * 1000;
  function oku(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function yaz(k, v) { try { if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }

  window.GeekRadyoOlustur = function (cfg) {
    cfg = cfg || {};
    var API = cfg.api, YEDEK = cfg.yedek;
    var audio = new Audio();
    audio.preload = 'none';
    audio.setAttribute('playsinline', '');
    var adres = '', ister = false, deniyor = false, yenidenSay = 0, yenidenZaman = null, aboneler = [], sorguZaman = null, ilkYuk = false;
    var d = { caliyor: false, ister: false, baglaniyor: false, sarki: 'Geek Radio', sanatci: '', art: '', canli: 'Canlı', ses: 70, not: '' };

    var v0 = parseInt(oku(SES_ANAHTAR), 10);
    d.ses = isNaN(v0) ? 70 : Math.max(0, Math.min(100, v0));
    audio.volume = d.ses / 100;

    function yayinla() {
      d.caliyor = !audio.paused && !audio.ended && audio.readyState >= 2;
      d.ister = ister;
      aboneler.slice().forEach(function (f) { try { f(d); } catch (e) {} });
      if ('mediaSession' in navigator) { try { navigator.mediaSession.playbackState = audio.paused ? 'paused' : 'playing'; } catch (e) {} }
    }
    function not_(m) { d.not = m || ''; }
    function niyetKaydet(v) {
      ister = !!v;
      yaz(DEPO, ister ? JSON.stringify({ i: 1, t: Date.now() }) : JSON.stringify({ i: 0, t: Date.now() }));
    }

    audio.addEventListener('playing', function () { yenidenSay = 0; deniyor = false; d.baglaniyor = false; not_(''); yayinla(); });
    audio.addEventListener('pause', yayinla);
    audio.addEventListener('waiting', function () {
      d.baglaniyor = true; yayinla();
      setTimeout(function () { if (ister && audio.readyState < 3 && !audio.paused) { deniyor = false; yeniden(); } }, 12000);
    });

    function kaynak(taze) { return taze ? adres + (adres.indexOf('?') > -1 ? '&' : '?') + 't=' + Date.now() : adres; }

    function cal(taze) {
      if (!adres) { oku_().then(function () { if (ister) cal(taze); }).catch(function () { adres = YEDEK; if (ister) cal(taze); }); return; }
      if (deniyor) return;
      deniyor = true; d.baglaniyor = true;
      if (taze || audio.getAttribute('data-k') !== adres) { audio.src = kaynak(taze); audio.setAttribute('data-k', adres); }
      var p = audio.play();
      if (p && p.then) {
        p.then(function () { deniyor = false; d.baglaniyor = false; yayinla(); }).catch(function (e) {
          deniyor = false; d.baglaniyor = false;
          if (e && e.name === 'NotAllowedError') { not_('Müzik için ekrana bir kez dokun ya da ▶ düğmesine bas.'); bekleyenDokunus = true; }
          else yeniden();
          yayinla();
        });
      }
    }
    var bekleyenDokunus = false, dokunusT = 0;
    function yeniden() {
      if (!ister || yenidenZaman) return;
      yenidenSay++;
      d.baglaniyor = true; not_('Bağlantı koptu, yeniden bağlanılıyor…'); yayinla();
      yenidenZaman = setTimeout(function () { yenidenZaman = null; if (ister) cal(true); }, Math.min(15000, 1500 * yenidenSay));
    }
    ['error', 'stalled', 'ended'].forEach(function (o) { audio.addEventListener(o, function () { if (ister) { deniyor = false; yeniden(); } }); });

    /* şu an çalan */
    function guncelle(j) {
      var np = j && j.now_playing && j.now_playing.song;
      if (np) {
        d.sarki = np.title || np.text || 'Geek Radio'; d.sanatci = np.artist || ''; d.art = np.art || '';
        if ('mediaSession' in navigator && window.MediaMetadata) {
          try { navigator.mediaSession.metadata = new MediaMetadata({ title: d.sarki, artist: d.sanatci || 'Geek Radio', album: 'Geek Radio', artwork: d.art ? [{ src: d.art }] : [] }); } catch (e) {}
        }
      }
      d.canli = (j && j.live && j.live.is_live) ? 'Canlı yayın' : 'Canlı';
    }
    function oku_() {
      return fetch(API, { cache: 'no-store' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (j) {
        guncelle(j);
        if (!adres) { var st = j.station || {}; adres = st.listen_url || (st.mounts && st.mounts[0] && st.mounts[0].url) || YEDEK; }
        yayinla(); return j;
      });
    }
    function sorguAyarla() {
      var gerek = ister || aboneler.length > 0;
      if (gerek && !sorguZaman) { sorguZaman = setInterval(function () { oku_().catch(function () {}); }, 15000); }
      else if (!gerek && sorguZaman) { clearInterval(sorguZaman); sorguZaman = null; }
    }

    var api = {
      durum: function () { return d; },
      abone: function (f) {
        aboneler.push(f); sorguAyarla();
        if (!adres) oku_().catch(function () { adres = YEDEK; });
        try { f(d); } catch (e) {}
        return function () { aboneler = aboneler.filter(function (x) { return x !== f; }); sorguAyarla(); };
      },
      cal: function () { niyetKaydet(true); not_(''); bekleyenDokunus = false; sorguAyarla(); cal(true); yayinla(); },
      durdur: function () {
        niyetKaydet(false); audio.pause(); clearTimeout(yenidenZaman); yenidenZaman = null; deniyor = false; d.baglaniyor = false; not_(''); sorguAyarla(); yayinla();
      },
      degistir: function () {
        if (Date.now() - dokunusT < 700) return;      // aynı dokunuş zaten başlattı (pointerdown → click çifti)
        if (ister && !audio.paused) api.durdur(); else api.cal();
      },
      sesAyarla: function (v) {
        v = Math.max(0, Math.min(100, parseInt(v, 10) || 0)); d.ses = v; audio.volume = v / 100; yaz(SES_ANAHTAR, String(v)); yayinla();
      },
      /* İlk kullanıcı dokunuşu: otomatik oynatma engellenmişse veya önceki oturumdan devam ediliyorsa başlatır. */
      dokunus: function () {
        if (ister && audio.paused && !deniyor) { bekleyenDokunus = false; dokunusT = Date.now(); cal(true); }
      },
      /* Önceki kullanımdan "çalıyordu" bilgisi varsa (6 saat içinde) devam etmeyi dener. */
      devam: function () {
        if (ilkYuk) return; ilkYuk = true;
        var k = null; try { k = JSON.parse(oku(DEPO) || 'null'); } catch (e) {}
        if (k && k.i === 1 && Date.now() - k.t < GECERLI_MS) { ister = true; sorguAyarla(); cal(true); }
      },
      /* Kullanıcı hiç durdurmadıysa (ör. Geek Crew sayfası) kendiliğinden başlatır. */
      otoBaslat: function () {
        var k = null; try { k = JSON.parse(oku(DEPO) || 'null'); } catch (e) {}
        if (k && k.i === 0) return false;                 // kullanıcı kendisi kapatmış
        if (!ister) api.cal();
        return true;
      },
      askiya: function () { audio.pause(); audio.removeAttribute('src'); audio.removeAttribute('data-k'); },
      el: audio,
      yerel: false
    };

    if ('mediaSession' in navigator) {
      try {
        navigator.mediaSession.setActionHandler('play', function () { api.cal(); });
        navigator.mediaSession.setActionHandler('pause', function () { api.durdur(); });
        navigator.mediaSession.setActionHandler('stop', function () { api.durdur(); });
      } catch (e) {}
    }
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && ister && audio.paused && adres && !deniyor) cal(true);
    });
    window.addEventListener('online', function () { if (ister && audio.paused && !deniyor) cal(true); });
    /* çalarken "hâlâ açık" damgasını tazele (6 saatlik devam penceresi) */
    setInterval(function () { if (ister && !audio.paused) yaz(DEPO, JSON.stringify({ i: 1, t: Date.now() })); }, 60000);
    return api;
  };

  /* Sayfaların kullandığı bulucu: kabuktaki oynatıcı varsa onu, yoksa sayfaya özel yerel oynatıcıyı döndürür. */
  window.GeekRadyoAl = function (cfg) {
    try { if (window.parent && window.parent !== window && window.parent.GeekRadyo) return window.parent.GeekRadyo; } catch (e) {}
    if (!window.GeekRadyo) {
      window.GeekRadyo = window.GeekRadyoOlustur(cfg || {});
      window.GeekRadyo.yerel = true;
      window.addEventListener('pagehide', function () { try { window.GeekRadyo.askiya(); } catch (e) {} });
    }
    return window.GeekRadyo;
  };
})();
