/* Kalıcı Geek Radio kabuğu: tek bir iframe içinde paneli açar, radyo oynatıcısını (window.GeekRadyo) sayfalar arası yaşatır.
   Radyo kullanıcı kendisi kapatana kadar çalar; çalarken sağ altta yüzen bir düğme + mini kontrol kartı görünür. */
(function () {
  'use strict';
  var cerceve = document.getElementById('uygulama');
  if (!cerceve) return;
  /* iç içe kabuğu engelle (ör. çevrimdışı önbellekten gelen kabuk iframe'in içinde açılırsa) */
  if (window.top !== window.self) { document.body.innerHTML = '<p style="font:14px system-ui;padding:1rem">Sayfa yüklenemedi, lütfen yenileyin.</p>'; return; }

  var cfg = {};
  try { cfg = JSON.parse(document.getElementById('radyo-cfg').textContent); } catch (e) {}
  var R = window.GeekRadyo = window.GeekRadyoOlustur(cfg);

  /* ---- adres ve başlık eşitleme + giriş sayfası kırılması ---- */
  var oncekiUrl = '';
  function esitle() {
    var w, doc;
    try { w = cerceve.contentWindow; doc = w.document; } catch (e) { return; }
    if (!w || !doc) return;
    if (doc.querySelector('meta[name="geek-giris"]')) {             // oturum bitti/çıkış yapıldı → kabuktan çık
      try { window.location.replace(w.location.href); } catch (e) { window.location.reload(); }
      return;
    }
    var u = w.location.pathname + w.location.search + w.location.hash;
    if (u !== oncekiUrl && w.location.href !== 'about:blank') {
      oncekiUrl = u;
      try { history.replaceState(null, '', u); } catch (e) {}
    }
    if (doc.title) document.title = doc.title;
    var tc = doc.querySelector('meta[name="theme-color"]'), kc = document.querySelector('meta[name="theme-color"]');
    if (tc && kc) kc.setAttribute('content', tc.getAttribute('content'));
  }
  cerceve.addEventListener('load', function () {
    esitle();
    try {
      var w = cerceve.contentWindow;
      w.addEventListener('hashchange', esitle);
      w.addEventListener('popstate', esitle);
      new w.MutationObserver(function () { try { if (w.document.title) document.title = w.document.title; } catch (e) {} })
        .observe(w.document.querySelector('title') || w.document.head, { childList: true, subtree: true, characterData: true });
    } catch (e) {}
  });
  /* kabuğa odak/klavye: iframe dışına tıklanırsa iframe'e odak ver */
  window.addEventListener('focus', function () { try { cerceve.contentWindow.focus(); } catch (e) {} });

  /* ---- yüzen radyo düğmesi ---- */
  var kok = document.getElementById('radyo-kabuk');
  kok.innerHTML =
    '<div class="rk-kart" id="rk-kart" hidden role="dialog" aria-label="Geek Radio">' +
      '<div class="rk-ust"><div class="rk-kapak" id="rk-kapak" aria-hidden="true">G</div>' +
      '<div class="rk-metin"><div class="rk-etiket" id="rk-etiket">Geek Radio · Canlı</div><div class="rk-sarki" id="rk-sarki">Geek Radio</div><div class="rk-sanatci" id="rk-sanatci"></div></div></div>' +
      '<div class="rk-alt"><button type="button" class="rk-btn" id="rk-oynat" aria-label="Duraklat">❚❚</button>' +
      '<input type="range" class="rk-ses" id="rk-ses" min="0" max="100" aria-label="Ses düzeyi">' +
      '<button type="button" class="rk-kapat" id="rk-kapat">Radyoyu kapat</button></div>' +
      '<div class="rk-not" id="rk-not" hidden></div></div>' +
    '<button type="button" class="rk-dugme" id="rk-dugme" aria-label="Geek Radio kontrolleri" aria-expanded="false"><span class="rk-eq" aria-hidden="true"><i></i><i></i><i></i><i></i></span></button>';
  var $ = function (id) { return document.getElementById(id); };
  var kart = $('rk-kart'), dugme = $('rk-dugme'), oynat = $('rk-oynat'), ses = $('rk-ses'), art = $('rk-kapak');
  function kartAc(ac) { kart.hidden = !ac; dugme.setAttribute('aria-expanded', ac ? 'true' : 'false'); }
  dugme.addEventListener('click', function () { kartAc(kart.hidden); });
  document.addEventListener('pointerdown', function (e) { if (!kart.hidden && !kok.contains(e.target)) kartAc(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') kartAc(false); });
  /* iframe içindeki bir dokunuş da kartı kapatır */
  cerceve.addEventListener('load', function () { try { cerceve.contentDocument.addEventListener('pointerdown', function () { kartAc(false); }, true); } catch (e) {} });
  oynat.addEventListener('click', function () { R.degistir(); });
  ses.addEventListener('input', function () { R.sesAyarla(ses.value); });
  $('rk-kapat').addEventListener('click', function () { R.durdur(); kartAc(false); });

  var sonArt = null;
  R.abone(function (d) {
    var aktif = d.ister || d.caliyor;
    kok.hidden = !aktif;
    kok.classList.toggle('rk-caliyor', d.caliyor);
    kok.classList.toggle('rk-baglan', d.ister && !d.caliyor);
    if (!aktif && !kart.hidden) kartAc(false);
    $('rk-etiket').textContent = 'Geek Radio · ' + d.canli;
    $('rk-sarki').textContent = d.sarki; $('rk-sanatci').textContent = d.sanatci;
    oynat.textContent = d.ister ? '❚❚' : '▶'; oynat.setAttribute('aria-label', d.ister ? 'Duraklat' : 'Oynat');
    if (document.activeElement !== ses) ses.value = d.ses;
    var n = $('rk-not'); n.textContent = d.not; n.hidden = !d.not;
    if (d.art !== sonArt) {
      sonArt = d.art;
      if (d.art) { art.textContent = ''; var im = new Image(); im.alt = ''; im.onerror = function () { art.textContent = 'G'; }; im.src = d.art; art.appendChild(im); } else art.textContent = 'G';
    }
  });

  /* önceki oturumdan "çalıyordu" kaydı varsa ilk dokunuşta devam eder; kabuğun kendi dokunuşları da sayılır */
  R.devam();
  /* sayfa, oynatıcı hazır olduktan sonra yüklenir (yarış durumu olmasın) */
  cerceve.src = cerceve.getAttribute('data-src');
  ['pointerdown', 'keydown', 'touchstart'].forEach(function (ev) {
    document.addEventListener(ev, function () { R.dokunus(); }, { capture: true, passive: true });
  });
})();
