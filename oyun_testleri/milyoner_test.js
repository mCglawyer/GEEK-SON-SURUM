// Geek Milyoner veri/mantık testleri (tarayıcısız): node oyun_testleri/milyoner_test.js
const fs = require('fs'), path = require('path'), assert = require('assert');
const M = require(path.join(__dirname, '..', 'static', 'js', 'kosu', 'milyoner.js'));
let gecen = 0;
function t(ad, f) { try { f(); gecen++; console.log('  ok  ' + ad); } catch (e) { console.error('FAIL ' + ad + '\n' + e.stack); process.exitCode = 1; } }

t('ödül merdiveni sunucudakiyle aynı', () => {
  const v = fs.readFileSync(path.join(__dirname, '..', 'panel', 'views.py'), 'utf8');
  const m = v.match(/MILYONER_MERDIVEN = \(([^)]*)\)/);
  assert(m, 'sunucuda MILYONER_MERDIVEN yok');
  const sunucu = m[1].split(',').map(x => parseInt(x.trim(), 10));
  assert.deepStrictEqual(sunucu, M.MERDIVEN);
  assert.strictEqual(M.MERDIVEN.length, 15);
});
t('her seviyede en az 3 soru, her soru 1 doğru + 3 farklı yanlış', () => {
  assert.strictEqual(M.HAVUZ.length, 5);
  M.HAVUZ.forEach((h, ti) => {
    assert(h.length >= 3, 'seviye ' + ti);
    h.forEach(q => {
      assert.strictEqual(q.length, 5, q[0]);
      q.forEach(x => assert(typeof x === 'string' && x.trim().length > 0, q[0]));
      assert.strictEqual(new Set(q.slice(1)).size, 4, 'şıklar tekrar ediyor: ' + q[0]);
    });
  });
});
t('tekrar eden soru yok', () => {
  const hepsi = M.HAVUZ.flat().map(q => q[0]);
  assert.strictEqual(new Set(hepsi).size, hepsi.length);
});
t('oyunSorulari: 15 soru, seviye sırası, tek doğru şık', () => {
  for (let n = 0; n < 50; n++) {
    const s = M.oyunSorulari();
    assert.strictEqual(s.length, 15);
    s.forEach((q, i) => {
      assert.strictEqual(q.tier, Math.floor(i / 3));
      assert.strictEqual(q.siklar.length, 4);
      assert.strictEqual(q.siklar.filter(x => x.d).length, 1);
    });
    assert.strictEqual(new Set(s.map(q => q.s)).size, 15);
  }
});
t('seyirci oyu: yüzdeler 100, elenen şıkka oy yok', () => {
  for (let n = 0; n < 200; n++) {
    const q = M.oyunSorulari()[n % 15];
    const elenen = [false, false, false, false]; let k = 0;
    q.siklar.forEach((s, i) => { if (!s.d && k < 2 && n % 2) { elenen[i] = true; k++; } });
    const pay = M.seyirciOyu(q, elenen);
    let top = 0; Object.keys(pay).forEach(i => { assert(!elenen[i]); assert(pay[i] >= 0); top += pay[i]; });
    assert.strictEqual(top, 100);
  }
});
t('seyirci kolay soruda çoğunlukla doğruyu söyler', () => {
  let dogru = 0;
  for (let n = 0; n < 300; n++) {
    const q = M.oyunSorulari()[0]; const pay = M.seyirciOyu(q, [false, false, false, false]);
    const en = Object.keys(pay).sort((a, b) => pay[b] - pay[a])[0];
    if (q.siklar[en].d) dogru++;
  }
  assert(dogru > 250, 'doğru oranı düşük: ' + dogru);
});
t('telefon cevabı metin döndürür ve şık harfi içerir', () => {
  const q = M.oyunSorulari()[3]; const c = M.telefonCevabi(q, [false, false, false, false]);
  assert(/[ABCD] diyorum/.test(c), c);
});
t('puan biçimi', () => { assert.strictEqual(M.puanYaz(1000000), '1.000.000'); assert.strictEqual(M.puanYaz(100), '100'); });
console.log(gecen + ' test geçti');
