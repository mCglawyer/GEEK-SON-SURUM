/* PDF / Excel indirme bağlantıları: sayfadan ayrılmadan açar, "Geri" düğmesi sunar.
   - Excel: arka planda indirir, sayfa yerinde kalır (uygulamada geri dönüş sorunu olmaz).
   - PDF (bilgisayar): sayfa içinde tam ekran önizleme + Geri / İndir düğmeleri.
   - PDF (telefon): indirir; tarayıcı PDF'i iframe'de gösteremediği için önizleme yok.
   Herhangi bir hata olursa bağlantı normal şekilde açılır. */
(function () {
  var DESEN = /(\/excel\/|\/pdf\/|\/indir\/|[?&]bicim=(xlsx|pdf)\b)/i;
  var acik = null;

  function toast(m) {
    var t = document.createElement('div');
    t.className = 'dosya-toast'; t.textContent = m; document.body.appendChild(t);
    setTimeout(function () { t.classList.add('git'); }, 2200);
    setTimeout(function () { t.remove(); }, 2700);
  }
  function ad(yanit, url) {
    var cd = yanit.headers.get('Content-Disposition') || '', m;
    if ((m = /filename\*=UTF-8''([^;]+)/i.exec(cd))) { try { return decodeURIComponent(m[1]); } catch (e) {} }
    if ((m = /filename="?([^";]+)"?/i.exec(cd))) return m[1];
    return (url.split('?')[0].split('/').filter(Boolean).pop() || 'dosya');
  }
  function indir(blob, dosya) {
    var u = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = u; a.download = dosya; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(u); }, 60000);
  }
  function kapat(geriGit) {
    if (!acik) return;
    var o = acik; acik = null;
    URL.revokeObjectURL(o.url); o.el.remove();
    document.documentElement.classList.remove('dosya-acik');
    if (geriGit && history.state && history.state.dosyaOnizleme) history.back();
  }
  function onizle(blob, dosya) {
    var url = URL.createObjectURL(blob), el = document.createElement('div');
    el.className = 'dosya-onizleme';
    el.innerHTML = '<div class="dosya-bar"><button type="button" class="btn btn-ghost btn-mini" data-geri>← Geri</button>' +
      '<span class="dosya-ad"></span><button type="button" class="btn btn-primary btn-mini" data-indir>İndir</button></div>' +
      '<iframe title="Önizleme"></iframe>';
    el.querySelector('.dosya-ad').textContent = dosya;
    el.querySelector('iframe').src = url;
    el.querySelector('[data-geri]').onclick = function () { kapat(true); };
    el.querySelector('[data-indir]').onclick = function () { indir(blob, dosya); };
    document.body.appendChild(el);
    document.documentElement.classList.add('dosya-acik');
    acik = { el: el, url: url };
    try { history.pushState({ dosyaOnizleme: 1 }, ''); } catch (e) {}
  }

  window.addEventListener('popstate', function () { if (acik) kapat(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') kapat(true); });

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a || e.defaultPrevented || e.button || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (a.dataset.dosyaYok != null) return;
    var u; try { u = new URL(a.href, location.href); } catch (x) { return; }
    if (u.origin !== location.origin || !DESEN.test(u.pathname + u.search)) return;
    if (!window.fetch || !window.Blob) return;
    e.preventDefault();
    var eski = a.textContent; a.classList.add('dosya-bekle'); a.setAttribute('aria-busy', 'true');
    fetch(u.href, { credentials: 'same-origin' }).then(function (r) {
      var tur = (r.headers.get('Content-Type') || '').toLowerCase();
      if (!r.ok || tur.indexOf('text/html') === 0) throw new Error('dosya değil');
      return r.blob().then(function (b) { return { b: b, ad: ad(r, u.pathname), tur: tur }; });
    }).then(function (d) {
      var pdf = d.tur.indexOf('pdf') > -1;
      var masaustu = window.matchMedia && matchMedia('(pointer:fine)').matches && !/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
      if (pdf && masaustu) onizle(d.b, d.ad);
      else { indir(d.b, d.ad); toast('İndirildi: ' + d.ad); }
    }).catch(function () {
      window.location.href = u.href;                 // yedek: normal açılış
    }).then(function () { a.classList.remove('dosya-bekle'); a.removeAttribute('aria-busy'); });
  });
})();
