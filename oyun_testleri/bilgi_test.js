/* Geek Bilgi Yarışması soru bankası testi: node oyun_testleri/bilgi_test.js */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const d = path.join(__dirname, '..', 'static', 'js', 'kosu');
for (const f of fs.readdirSync(d).filter(x => /^sorular_.*\.js$/.test(x))) require(path.join(d, f));
const S = globalThis.GeekKosu.sorular;
let toplam = 0; const gorulen = new Set();
for (const c of S) {
  for (const l of c.q.split('\n').map(x => x.trim()).filter(Boolean)) {
    const a = l.split('|');
    assert.strictEqual(a.length, 7, c.k + ': alan sayısı: ' + l.slice(0, 60));
    assert.ok(+a[0] >= 1 && +a[0] <= 5, 'zorluk: ' + l.slice(0, 60));
    assert.strictEqual(new Set(a.slice(2, 6)).size, 4, 'şıklar tekrar: ' + l.slice(0, 60));
    assert.ok(a[6].length >= 40, 'açıklama kısa: ' + l.slice(0, 60));
    assert.ok(!gorulen.has(a[1]), 'tekrar soru: ' + a[1]); gorulen.add(a[1]);
    toplam++;
  }
}
assert.ok(S.length >= 11, 'kategori sayısı');
assert.ok(toplam >= 1000, 'en az 1000 soru: ' + toplam);
console.log('  ok  ' + toplam + ' soru, ' + S.length + ' kategori');
console.log('1 test geçti');
