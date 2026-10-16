/* Geek Radio kartı (Geek Crew sayfası) — kalıcı kabuktaki ortak oynatıcıyı (window.parent.GeekRadyo) kullanır.
   Kabuk yoksa sayfaya özel yerel oynatıcı kurulur. Çalmaya başlayınca diğer sayfalarda da çalmaya devam eder;
   kullanıcı kendisi ❚❚ ile (ya da sağ alttaki yüzen düğmeden) kapatana kadar sürer.
   Not: Tarayıcılar sesli otomatik oynatmayı bazen engeller; o durumda ilk dokunuşta başlar. */
(function () {
  var kok = document.getElementById('radyo');
  if (!kok || !window.GeekRadyoAl) return;
  var R = GeekRadyoAl({ api: kok.dataset.api, yedek: kok.dataset.yedek, sayfa: kok.dataset.sayfa });
  var $ = function (id) { return document.getElementById(id); };
  var btn = $('radyo-oynat'), ses = $('radyo-ses'), sarki = $('radyo-sarki'), sanatci = $('radyo-sanatci'),
      canli = $('radyo-canli'), art = $('radyo-art'), not_ = $('radyo-not');

  R.abone(function (d) {
    kok.classList.toggle('caliyor', d.caliyor);
    btn.textContent = d.ister ? '❚❚' : '▶';
    btn.setAttribute('aria-label', d.ister ? 'Duraklat' : 'Oynat');
    sarki.textContent = d.sarki; sanatci.textContent = d.sanatci;
    canli.textContent = '● ' + d.canli;
    if (d.art) { if (art.getAttribute('src') !== d.art) { art.src = d.art; art.onerror = function () { art.hidden = true; }; } art.hidden = false; } else art.hidden = true;
    if (document.activeElement !== ses) ses.value = d.ses;
    not_.textContent = d.not || ''; not_.hidden = !d.not;
  });
  btn.addEventListener('click', function () { R.degistir(); });
  ses.addEventListener('input', function () { R.sesAyarla(ses.value); });

  /* Sayfa açılınca kullanıcı radyoyu kendisi kapatmadıysa kendiliğinden başlat. */
  if (!R.durum().ister) R.otoBaslat();
})();
