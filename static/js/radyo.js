/* Geek Radio — Geek Crew sayfasına gömülü canlı yayın oynatıcı (AzuraCast).
   Sayfa açılınca kendiliğinden başlar ve sayfada kaldığı sürece çalmaya devam eder:
   bağlantı koparsa yeniden bağlanır, sekmeye dönünce kaldığı yerden sürer.
   Not: Tarayıcılar sesli otomatik oynatmayı bazen engeller; o durumda ilk dokunuş/tıklamada başlar. */
(function () {
  var kok = document.getElementById('radyo');
  if (!kok) return;
  var API = kok.dataset.api, YEDEK = kok.dataset.yedek, SAYFA = kok.dataset.sayfa;
  var $ = function (id) { return document.getElementById(id); };
  var btn = $('radyo-oynat'), ses = $('radyo-ses'), sarki = $('radyo-sarki'), sanatci = $('radyo-sanatci'),
      canli = $('radyo-canli'), art = $('radyo-art'), kapak = $('radyo-kapak'), not_ = $('radyo-not');

  var audio = new Audio();
  audio.preload = 'none';
  var adres = '', ister = true, deniyor = false, yenidenSay = 0, yenidenZaman = null;

  function dep(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {} return null; }
  function oturum(k, v) { try { if (v === undefined) return sessionStorage.getItem(k); if (v === null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, v); } catch (e) {} return null; }
  function bildir(m) { not_.textContent = m || ''; not_.hidden = !m; }

  var v0 = parseInt(dep('geek_radyo_ses'), 10);
  ses.value = isNaN(v0) ? 70 : v0; audio.volume = ses.value / 100;
  ses.addEventListener('input', function () { audio.volume = ses.value / 100; dep('geek_radyo_ses', ses.value); });

  function arayuz() {
    var cal = !audio.paused && !audio.ended;
    kok.classList.toggle('caliyor', cal);
    btn.textContent = cal ? '❚❚' : '▶';
    btn.setAttribute('aria-label', cal ? 'Duraklat' : 'Oynat');
  }
  audio.addEventListener('playing', function () { yenidenSay = 0; deniyor = false; bildir(''); arayuz(); });
  audio.addEventListener('pause', arayuz);

  function kaynak(taze) {
    return taze ? adres + (adres.indexOf('?') > -1 ? '&' : '?') + 't=' + Date.now() : adres;
  }
  function cal(taze) {
    if (!adres || deniyor) return;
    deniyor = true;
    if (taze || audio.src !== adres) audio.src = kaynak(taze);
    var p = audio.play();
    if (p && p.then) {
      p.then(function () { deniyor = false; arayuz(); }).catch(function (e) {
        deniyor = false;
        if (e && e.name === 'NotAllowedError') {            // otomatik oynatma engellendi → ilk etkileşimde başlat
          bildir('Müzik için ekrana bir kez dokun ya da ▶ düğmesine bas.');
          bekleyen();
        } else { yeniden(); }
        arayuz();
      });
    }
  }
  function bekleyen() {
    var ev = ['pointerdown', 'keydown', 'touchstart'];
    function basla() {
      ev.forEach(function (x) { document.removeEventListener(x, basla, true); });
      if (ister && audio.paused) cal(true);
    }
    ev.forEach(function (x) { document.addEventListener(x, basla, true); });
  }
  function yeniden() {
    if (!ister || yenidenZaman) return;
    yenidenSay++;
    var bekle = Math.min(15000, 1500 * yenidenSay);
    bildir('Bağlantı koptu, yeniden bağlanılıyor…');
    yenidenZaman = setTimeout(function () { yenidenZaman = null; if (ister) cal(true); }, bekle);
  }
  ['error', 'stalled', 'ended'].forEach(function (o) { audio.addEventListener(o, function () { if (ister) { deniyor = false; yeniden(); } }); });
  audio.addEventListener('waiting', function () {
    setTimeout(function () { if (ister && audio.readyState < 3 && !audio.paused) { deniyor = false; yeniden(); } }, 12000);
  });

  btn.addEventListener('click', function () {
    if (!audio.paused) { ister = false; audio.pause(); oturum('geek_radyo_durdu', '1'); bildir(''); }
    else { ister = true; oturum('geek_radyo_durdu', null); bildir(''); cal(true); }
    arayuz();
  });
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && ister && audio.paused && adres) cal(true);
  });

  /* Şu an çalan parça */
  function guncelle(d) {
    var np = d && d.now_playing && d.now_playing.song;
    if (np) {
      sarki.textContent = np.title || np.text || 'Geek Radio';
      sanatci.textContent = np.artist || '';
      if (np.art) { art.src = np.art; art.hidden = false; art.onerror = function () { art.hidden = true; }; } else art.hidden = true;
      if ('mediaSession' in navigator && window.MediaMetadata) {
        try { navigator.mediaSession.metadata = new MediaMetadata({ title: np.title || 'Geek Radio', artist: np.artist || 'Geek Radio',
          artwork: np.art ? [{ src: np.art }] : [] }); } catch (e) {}
      }
    }
    var l = d && d.live && d.live.is_live;
    canli.textContent = l ? '● Canlı yayın' : '● Canlı';
  }
  function oku() {
    return fetch(API, { cache: 'no-store' }).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (d) {
      guncelle(d);
      if (!adres) {
        var st = d.station || {};
        adres = st.listen_url || (st.mounts && st.mounts[0] && st.mounts[0].url) || YEDEK;
      }
      return d;
    });
  }
  if ('mediaSession' in navigator) {
    try {
      navigator.mediaSession.setActionHandler('play', function () { ister = true; oturum('geek_radyo_durdu', null); cal(true); });
      navigator.mediaSession.setActionHandler('pause', function () { ister = false; audio.pause(); oturum('geek_radyo_durdu', '1'); });
    } catch (e) {}
  }

  function baslat() {
    oku().catch(function () { adres = YEDEK; sarki.textContent = 'Geek Radio'; }).then(function () {
      if (oturum('geek_radyo_durdu') === '1') { ister = false; sarki.textContent = sarki.textContent === 'Bağlanıyor…' ? 'Geek Radio' : sarki.textContent; arayuz(); return; }
      cal(false);
    });
    setInterval(function () { oku().catch(function () {}); }, 15000);
  }
  window.addEventListener('pagehide', function () { ister = false; audio.pause(); audio.removeAttribute('src'); });
  baslat();
})();
