/* Geek Motor testleri: node oyun_testleri/motor_test.js */
'use strict';
const assert = require('assert');
const path = require('path');
const d = path.join(__dirname, '..', 'static', 'js', 'kosu', 'motor');
['tween', 'degisken', 'nesne', 'olay', 'sahne', 'efekt'].forEach(f => require(path.join(d, f + '.js')));
const M = globalThis.GeekKosu.motor;
let n = 0; function ok(ad, fn) { fn(); n++; console.log('  ok  ' + ad); }

ok('Tween: değer, ilerleme, bitiş geri çağrısı', () => {
  const t = new M.TweenYonetici(); let son = -1, bitti = 0;
  t.ekle('a', 0, 10, 1, 'linear', v => { son = v; }, () => { bitti++; });
  t.adim(0.5); assert.strictEqual(son, 5); assert.ok(t.oynuyor('a')); assert.strictEqual(t.ilerleme('a'), 0.5);
  t.adim(0.6); assert.strictEqual(son, 10); assert.ok(t.bitti('a')); assert.strictEqual(bitti, 1);
  t.adim(1); assert.strictEqual(bitti, 1);
});
ok('Tween: duraklat/devam, durdur(hedefe git), çok değerli, easing sınırları', () => {
  const t = new M.TweenYonetici(); let v = 0, dz = null;
  t.ekle('a', 0, 4, 2, 'linear', x => { v = x; });
  t.adim(1); t.duraklat('a'); t.adim(1); assert.strictEqual(v, 2); t.devam('a'); t.adim(0.5); assert.strictEqual(v, 3);
  t.durdur('a', true); assert.strictEqual(v, 4);
  t.cok('c', [0, 10], [1, 20], 1, 'easeOutQuad', x => { dz = x; }); t.adim(1); assert.deepStrictEqual(dz, [1, 20]);
  Object.keys(M.kolaylik).forEach(k => { assert.ok(Math.abs(M.kolaylik[k](0)) < 1e-9, k + '(0)'); assert.ok(Math.abs(M.kolaylik[k](1) - 1) < 1e-9, k + '(1)'); });
  const b = M.bezier(0.25, 0.1, 0.25, 1); assert.ok(Math.abs(b(0)) < 1e-9 && Math.abs(b(1) - 1) < 1e-9 && b(0.5) > 0.5);
});
ok('Değişken: yapı, dizi, json gidiş-dönüş', () => {
  const k = new M.DegiskenKabi('t:'); k.al('skor').ayarla(10).ekle(5); assert.strictEqual(k.al('skor').al(), 15);
  const y = k.al('y'); y.cocukAl('a').ayarla(1); y.cocukAl('b').ayarla('x'); assert.strictEqual(y.uzunluk(), 2);
  const dz = k.al('dz'); dz.itele(1); dz.itele('m'); dz.itele(true);
  assert.deepStrictEqual(M.Degisken.dene(y.json()).json(), { a: 1, b: 'x' }); assert.deepStrictEqual(dz.json(), [1, 'm', true]);
});
ok('Davranış yaşam döngüsü: onCreated, Pre/Post sırası, etkinleştir, onDestroy', () => {
  const log = [];
  M.Davranis.turet('Deneme', { onCreated() { log.push('c'); }, doStepPreEvents() { log.push('pre'); }, doStepPostEvents() { log.push('post'); },
    onActivate() { log.push('on'); }, onDeActivate() { log.push('off'); }, onDestroy() { log.push('d'); } });
  const s = new M.Sahne('s'); const o = s.nesneYarat('Oyuncu'); const b = o.davranisEkle('Deneme');
  s.olaylar.ekle({ eylem: () => log.push('olay') });
  s.adim(0.016); assert.deepStrictEqual(log, ['c', 'pre', 'olay', 'post']);
  log.length = 0; b.etkinlestir(false); s.adim(0.016); assert.deepStrictEqual(log, ['off', 'olay']);
  log.length = 0; b.etkinlestir(true); o.yoket(); s.adim(0.016); assert.deepStrictEqual(log, ['on', 'olay', 'd']);
  assert.strictEqual(s.nesneler('Oyuncu').length, 0);
});
ok('Sahne: nesne listeleri, etiket, en yakın, silme', () => {
  const s = new M.Sahne('s'); s.nesneYarat('Dusman', { x: 5, etiketler: ['kotu'] }); const y = s.nesneYarat('Dusman', { x: 1 }); s.nesneYarat('Para', { x: 0 });
  assert.strictEqual(s.nesneler('Dusman').length, 2); assert.strictEqual(s.etiketli('kotu').length, 1);
  assert.strictEqual(s.enYakin('Dusman', 0, 0, 0), y); y.yoket(); s.adim(0.01); assert.strictEqual(s.nesneler('Dusman').length, 1);
});
ok('Olaylar: koşul, bir kez, zamanlayıcı, alt olay, her()', () => {
  const s = new M.Sahne('s'); let a = 0, b = 0, c = 0, e = 0;
  s.olaylar.ekle({ kosul: () => true, eylem: () => a++ });
  s.olaylar.ekle({ kosul: () => true, bir: true, eylem: () => b++ });
  s.olaylar.ekle({ kosul: M.olay.zamanlayici('z', 0.5), eylem: () => c++ });
  s.olaylar.ekle({ kosul: M.olay.her(0.25), eylem: () => e++ });
  s.olaylar.ekle({ kosul: () => true, alt: [{ kosul: () => false, eylem: () => { throw new Error('olmamalı'); } }] });
  for (let i = 0; i < 20; i++) s.adim(0.1);
  assert.strictEqual(a, 20); assert.strictEqual(b, 1); assert.strictEqual(c, 1); assert.ok(e >= 6 && e <= 9, 'her=' + e);
});
ok('Zaman ölçeği ve dt sınırı', () => {
  const s = new M.Sahne('s'); s.zaman.olcek = 0.5; s.adim(0.04); assert.ok(Math.abs(s.zaman.toplam - 0.02) < 1e-9);
  s.adim(5); assert.ok(s.zaman.ham <= 0.1 + 1e-9);
});
ok('SahneYigini: push duraklatır, pop devam ettirir, replace', () => {
  const log = [], y = new M.SahneYigini();
  const mk = ad => ({ onGir: () => log.push('gir:' + ad), onCik: () => log.push('cik:' + ad), onDuraklat: () => log.push('dur:' + ad), onDevam: () => log.push('dev:' + ad), onAdim: () => log.push('adim:' + ad) });
  y.tanimla('menu', mk('menu')).tanimla('oyun', mk('oyun')).tanimla('dur', mk('dur')).tanimla('bitis', mk('bitis'));
  y.push('menu'); y.replace('oyun'); y.push('dur'); y.adim(0.01);
  assert.deepStrictEqual(y.adlar(), ['oyun', 'dur']); assert.strictEqual(log.filter(x => x === 'adim:oyun').length, 0);
  y.pop(); y.adim(0.01); assert.strictEqual(y.mevcutAd(), 'oyun'); assert.ok(log.indexOf('dev:oyun') >= 0 && log.indexOf('adim:oyun') >= 0);
  y.replace('bitis', null, true); assert.deepStrictEqual(y.adlar(), ['bitis']); assert.ok(log.indexOf('cik:oyun') >= 0);
  assert.throws(() => y.push('yok'));
});
ok('EfektZinciri: GLSL birleştirme sırası ve uniform paylaşımı', () => {
  const T = { Vector2: function (x, y) { this.x = x; this.y = y; this.set = (a, b) => { this.x = a; this.y = b; }; }, Vector3: function (x, y, z) { this.x = x; this.y = y; this.z = z; this.set = (a, b, c) => { this.x = a; this.y = b; this.z = c; }; },
    ShaderMaterial: function (o) { Object.assign(this, o); this.dispose = () => {}; } };
  const z = new M.EfektZinciri(T, {}); z.p = { mBirlestir: null };
  z.ekle('Vinyet').ekle('Hareket').ekle('Tonlama', { poz: 0.8 }).ekle('Bloom');
  z._derle(); const f = z.p.mBirlestir.fragmentShader;
  assert.ok(f.indexOf('fx_taban(vUv') < f.indexOf('c = fx_Bloom') && f.indexOf('c = fx_Bloom') < f.indexOf('c = fx_Tonlama') && f.indexOf('c = fx_Tonlama') < f.indexOf('c = fx_Vinyet'));
  assert.strictEqual(z.u.poz.value, 0.8); assert.ok(z.p.mBirlestir.uniforms.vig === z.u.vig);
  z.kaldir('Vinyet'); z._derle(); assert.ok(z.p.mBirlestir.fragmentShader.indexOf('fx_Vinyet(vUv') < 0);
  assert.throws(() => z.ekle('Yok'));
});
console.log(n + ' test geçti');
