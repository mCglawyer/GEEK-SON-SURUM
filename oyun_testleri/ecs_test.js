/* Geek Oyun ECS/sistem testleri: node oyun_testleri/ecs_test.js */
'use strict';
const assert = require('assert');
const path = require('path');
const d = path.join(__dirname, '..', 'static', 'js', 'kosu');
require(path.join(d, 'ecs.js')); require(path.join(d, 'veri.js')); require(path.join(d, 'sistemler.js'));
const NS = globalThis.GeekKosu, S = NS.sistemler, V = NS.veri;

function tohum(s) { return function () { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; }; }
function dunya(mod) { const w = new NS.Dunya(mod); w.rastgele = tohum(7); S.kur(w); return w; }
function adim(w, n, dt) { for (let i = 0; i < n; i++) w.calistir(dt || 0.05); }
let sayac = 0;
function t(ad, fn) { try { fn(); sayac++; console.log('  ok  ' + ad); } catch (e) { console.error('  HATA ' + ad + '\n', e); process.exitCode = 1; } }

t('ECS: sorgu, yoket, gözlemci', () => {
  const w = new NS.Dunya('arena'); let dogdu = 0, oldu = 0;
  w.on('varlik_dogdu', () => dogdu++); w.on('varlik_oldu', () => oldu++);
  const a = w.yarat({ C_A: {}, C_B: {} });
  let b = w.yarat({ C_A: {} });
  assert.strictEqual(w.sorgu(['C_A']).length, 2); assert.strictEqual(w.sorgu(['C_A', 'C_B']).length, 1);
  w.yoket(b); w.temizle();
  assert.strictEqual(w.sorgu(['C_A']).length, 1); assert.strictEqual(dogdu, 2); assert.strictEqual(oldu, 1);
  w.ekle(b = w.yarat({}), 'C_B', {}); assert.strictEqual(w.sorgu(['C_B']).length, 2);
});

t('Stamina: atılma harcar, gecikmeden sonra yenilenir', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  S.castIste(w, o, 'dash', { x: 5, z: 0 }); adim(w, 1);
  assert.ok(o.c.C_Stamina.v <= 70.1, 'stamina düşmeli');
  assert.ok(o.c.C_Durum.dokunulmaz > 0.2, 'dokunulmaz olmalı');
  const x0 = o.c.C_Transform.x; adim(w, 4);
  assert.ok(o.c.C_Transform.x > x0 + 2, 'atılma hareket ettirmeli');
  adim(w, 40); assert.ok(o.c.C_Stamina.v > 90, 'stamina yenilenmeli: ' + o.c.C_Stamina.v);
});

t('Yetenek: ether yetmezse reddedilir, bekleme çalışır', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let ret = [];
  w.on('cast_reddedildi', (r) => ret.push(r.neden));
  o.c.C_Ether.v = 5; S.castIste(w, o, 'top', { x: 0, z: -9 }); adim(w, 1);
  assert.deepStrictEqual(ret, ['ether']);
  o.c.C_Ether.v = 100; S.castIste(w, o, 'top', { x: 0, z: -9 }); adim(w, 1);
  assert.ok(o.c.C_Ether.v < 90 && o.c.C_Yetenek.cd.top > 0.3);
  S.castIste(w, o, 'top', { x: 0, z: -9 }); adim(w, 1);
  assert.strictEqual(ret[1], 'bekleme');
  S.castIste(w, o, 'firtina', {x:0,z:-3}); adim(w,1); // arena'da açık
  assert.strictEqual(ret.length, 2);
});

t('Mod: fırtına Koşu modunda kullanılamaz', () => {
  const w = dunya('kosu'), o = w.olustur('oyuncu', {}); let ret = [];
  w.on('cast_reddedildi', (r) => ret.push(r.neden));
  S.castIste(w, o, 'firtina', { x: 0, z: -5 }); adim(w, 1); assert.deepStrictEqual(ret, ['mod']);
});

t('Kavurma topu düşmana çarpar, hasar verir, yanık uygular', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  const g = w.olustur('dusman', { tip: 'goblin', x: 0, z: -8, dalga: 1 });
  g.c.C_YZ.durum = 'bekle'; const hp0 = g.c.C_Can.hp;
  S.castIste(w, o, 'top', { x: 0, z: -8 }); adim(w, 12, 0.03);
  assert.ok(g.c.C_Can.hp < hp0 - 15, 'hasar: ' + g.c.C_Can.hp);
  assert.ok(g.c.C_Durum.yanik > 0 || g.c.C_Element.tur === 'pyro');
});

t('Hızlı mermi ince hedefi atlamaz (segment testi)', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  const g = w.olustur('dusman', { tip: 'jole', x: 0, z: -6, dalga: 1 });
  g.c.C_YZ.durum = 'bekle'; const hp0 = g.c.C_Can.hp;
  S.castIste(w, o, 'top', { x: 0, z: -6 }); adim(w, 3, 0.25);   // büyük adım
  assert.ok(g.c.C_Can.hp < hp0);
});

t('Tepkime: su + ateş = buhar çarpanı; elektrik + su = sersemletme', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  const g = w.olustur('dusman', { tip: 'kral', x: 0, z: -30, dalga: 1 }); let tep = [];
  w.on('hasar_uygulandi', (e) => { if (e.tepkime) tep.push(e.tepkime.id); });
  S.hasarIste(w, g, 10, { kaynak: o, element: 'hydro' }); adim(w, 1);
  const hp1 = g.c.C_Can.hp; S.hasarIste(w, g, 10, { kaynak: o, element: 'pyro' }); adim(w, 1);
  assert.strictEqual(tep[0], 'buhar'); assert.ok(Math.abs(hp1 - g.c.C_Can.hp - 16) < 0.2, 'buhar x1.6');
  S.hasarIste(w, g, 5, { kaynak: o, element: 'hydro' }); adim(w, 1);
  S.hasarIste(w, g, 5, { kaynak: o, element: 'electro' }); adim(w, 1);
  assert.strictEqual(tep[1], 'sok'); assert.ok(g.c.C_Durum.stun > 0.5);
});

t('Aşırı yük yakındaki düşmanlara alan hasarı verir', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  const a = w.olustur('dusman', { tip: 'kral', x: 0, z: -20 }), b = w.olustur('dusman', { tip: 'jole', x: 1.5, z: -20 });
  const hb = b.c.C_Can.hp;
  S.hasarIste(w, a, 5, { kaynak: o, element: 'pyro' }); adim(w, 1);
  S.hasarIste(w, a, 5, { kaynak: o, element: 'electro' }); adim(w, 1);
  assert.ok(b.c.C_Can.hp < hb, 'komşu zarar görmeli');
});

t('Köpük kalkan hasarı emer ve kırılır', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let kirildi = 0;
  w.on('kalkan_kirildi', () => kirildi++);
  S.castIste(w, o, 'kalkan'); adim(w, 1); assert.strictEqual(o.c.C_Durum.kalkan, 60);
  S.hasarIste(w, o, 40, {}); adim(w, 1); assert.strictEqual(o.c.C_Can.hp, 100); assert.strictEqual(o.c.C_Durum.kalkan, 20);
  o.c.C_Durum.dokunulmaz = 0;
  S.hasarIste(w, o, 50, {}); adim(w, 1); assert.strictEqual(kirildi, 1); assert.strictEqual(o.c.C_Can.hp, 70);
});

t('Yaralanma sonrası kısa dokunulmazlık; atılma sırasında hasar yok', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  S.hasarIste(w, o, 20, {}); S.hasarIste(w, o, 20, {}); adim(w, 1);
  assert.strictEqual(o.c.C_Can.hp, 80);
  adim(w, 20); S.hasarIste(w, o, 20, {}); adim(w, 1); assert.strictEqual(o.c.C_Can.hp, 60);
});

t('Şimşek en yakın hedefe çarpar ve zincirler', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let z = null;
  w.on('simsek', (e) => { z = e; });
  const a = w.olustur('dusman', { tip: 'jole', x: 0, z: -5 }), b = w.olustur('dusman', { tip: 'jole', x: 3, z: -7 }), c = w.olustur('dusman', { tip: 'jole', x: -3, z: -9 });
  const far = w.olustur('dusman', { tip: 'jole', x: 15, z: 15 });
  [a, b, c, far].forEach((e) => { e.c.C_YZ.durum = 'bekle'; });
  S.castIste(w, o, 'simsek', { x: 0, z: -5 }); adim(w, 1);
  assert.strictEqual(z.vurulan.length, 3); assert.ok(a.c.C_Can.hp < 42 && b.c.C_Can.hp < 42 && c.c.C_Can.hp < 42);
  assert.strictEqual(far.c.C_Can.hp, far.c.C_Can.max);
});

t('Patlama alanı itme ve hasar verir', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  const a = w.olustur('dusman', { tip: 'goblin', x: 0, z: -6 }); a.c.C_YZ.durum = 'bekle';
  S.castIste(w, o, 'patlama', { x: 0, z: -6 }); adim(w, 1);
  assert.ok(a.c.C_Can.hp < a.c.C_Can.max - 25); adim(w, 3); assert.ok(a.c.C_Transform.z < -6.2, 'itilmeli');
});

t('Fırtına alanı belirli aralıkla hasar verir ve biter', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let bitti = 0; w.on('alan_bitti', () => bitti++);
  const a = w.olustur('dusman', { tip: 'kral', x: 0, z: -8 }); a.c.C_YZ.durum = 'bekle';
  S.castIste(w, o, 'firtina', { x: 0, z: -8 }); adim(w, 1);
  const hp = a.c.C_Can.hp; adim(w, 50, 0.1); assert.ok(a.c.C_Can.hp < hp - 20); assert.strictEqual(bitti, 1);
});

t('Yapay zeka: 15 birim içinde fark eder, kovalar, vurur', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let fark = 0; w.on('fark_etti', () => fark++);
  const far = w.olustur('dusman', { tip: 'goblin', x: 0, z: 30 }); adim(w, 5); assert.strictEqual(fark, 0);
  const g = w.olustur('dusman', { tip: 'goblin', x: 0, z: -12 });
  adim(w, 100, 0.05);
  assert.strictEqual(fark >= 1, true);
  assert.ok(o.c.C_Can.hp < 100, 'goblin vurmalı: ' + o.c.C_Can.hp);
});

t('Kral jöle yere vurur ve canı azalınca jöle doğurur', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', { ozellik: { canRegen: 0 } }); let vurus = 0, dogur = 0;
  w.on('yere_vurus', () => vurus++); w.on('dusman_dogur', () => dogur++);
  const k = w.olustur('dusman', { tip: 'kral', x: 0, z: -6 });
  adim(w, 120, 0.05); assert.ok(vurus >= 1, 'yere vuruş');
  o.c.C_Can.hp = o.c.C_Can.max = 100000; o.c.C_Durum.dokunulmaz = 0;
  k.c.C_Can.hp = k.c.C_Can.max * 0.6; adim(w, 2); assert.strictEqual(dogur, 1);
  assert.ok(w.sorgu(['C_YZ']).filter((e) => e.c.C_YZ.tip === 'jole').length >= 3);
});

t('Dalga: başlar, düşman doğurur, hepsi ölünce biter ve puan verir', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let basla = 0, bit = 0;
  w.on('dalga_basladi', () => basla++); w.on('dalga_bitti', () => bit++);
  o.c.C_Can.hp = o.c.C_Can.max = 1e6; o.c.C_Durum.guc = 0;
  adim(w, 100, 0.05); assert.strictEqual(basla, 1);
  assert.ok(w.sorgu(['C_YZ']).length >= 3);
  w.sorgu(['C_YZ']).forEach((e) => S.hasarIste(w, e, 99999, { kaynak: o })); adim(w, 2);
  for (let i = 0; i < 80 && !bit; i++) { adim(w, 1, 0.05); w.sorgu(['C_YZ']).forEach((e) => S.hasarIste(w, e, 99999, { kaynak: o })); }
  assert.strictEqual(bit, 1); assert.ok(w.durum.skor > 50);
});

t('Dalga planı: her 5. dalgada patron', () => {
  assert.ok(S.dalgaPlani(5).liste.indexOf('kral') >= 0 && S.dalgaPlani(5).boss);
  assert.ok(S.dalgaPlani(4).liste.indexOf('kral') < 0);
  assert.ok(S.dalgaPlani(1).liste.every((x) => x === 'jole'));
});

t('Ölüm: puan, kombo çarpanı, düşenler, çekirdek ether verir', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let puan = [];
  w.on('puan', (p) => puan.push(p));
  for (let i = 0; i < 6; i++) { const e = w.olustur('dusman', { tip: 'jole', x: 3, z: 0 }); e.c.C_YZ.durum = 'bekle'; S.hasarIste(w, e, 9999, { kaynak: o }); }
  adim(w, 1); assert.strictEqual(puan.length, 6); assert.ok(puan[5].carpan > 1, 'kombo çarpanı');
  o.c.C_Ether.v = 10; adim(w, 30, 0.05); assert.ok(o.c.C_Ether.v > 20, 'çekirdek toplanmalı: ' + o.c.C_Ether.v);
});

t('Oyuncu ölünce oyuncu_oldu yayımlanır, düşman donar', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); let oldu = 0; w.on('oyuncu_oldu', () => oldu++);
  S.hasarIste(w, o, 500, {}); adim(w, 2); assert.strictEqual(oldu, 1); assert.ok(w.durum.bitti);
  const g = w.olustur('dusman', { tip: 'goblin', x: 1, z: 1 }); const z0 = g.c.C_Transform.z; adim(w, 20); assert.strictEqual(g.c.C_Transform.z, z0);
});

t('Arena sınırı: oyuncu dışarı çıkamaz', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {});
  o.c.C_Hiz.vx = 50; adim(w, 30); const p = o.c.C_Transform; assert.ok(Math.hypot(p.x, p.z) <= 22 - 0.5 + 1e-6);
});

t('Sunak: etkileşim güç verir; ocak ether yeniler', () => {
  const w = dunya('arena'), o = w.olustur('oyuncu', {}); const s = w.olustur('prop', { tip: 'sunak', x: 1, z: 0 }), oc = w.olustur('prop', { tip: 'ocak', x: 2, z: 1 });
  o.c.C_Ether.v = 10; adim(w, 10, 0.1); assert.ok(o.c.C_Ether.v > 20);
  assert.ok(w.durum.etkilesim && w.durum.etkilesim.tip === 'sunak');
  w.iste('etkilesim', {}); adim(w, 1); assert.ok(o.c.C_Durum.guc > 15); assert.strictEqual(s.c.C_Etkilesim.hazir, false);
  const g = w.olustur('dusman', { tip: 'kral', x: 0, z: -30 }); g.c.C_YZ.durum = 'bekle'; const h0 = g.c.C_Can.hp;
  S.hasarIste(w, g, 10, { kaynak: o }); adim(w, 1); assert.strictEqual(h0 - g.c.C_Can.hp, 15, 'güç x1.5');
});

t('Koşu: mermi engeli kırar, engel ölümü yayımlanır', () => {
  const w = dunya('kosu'), o = w.olustur('oyuncu', {}); let olen = 0;
  w.on('olum', (e) => { if (e.varlik.c.C_Engel) olen++; });
  const e = w.olustur('engel', { x: 0, z: -9, r: 1, can: 20 });
  S.castIste(w, o, 'top', null, { x: 0, z: -1 }); adim(w, 20, 0.03); assert.strictEqual(olen, 1); assert.ok(e.olu);
});

t('Koşu: patlama ileriyi temizler', () => {
  const w = dunya('kosu'), o = w.olustur('oyuncu', {}); let olen = 0; w.on('olum', (e) => { if (e.varlik.c.C_Engel) olen++; });
  w.olustur('engel', { x: -2.4, z: -8, r: 1, can: 20 }); w.olustur('engel', { x: 2.4, z: -9, r: 1, can: 20 }); w.olustur('engel', { x: 0, z: -40, r: 1, can: 20 });
  o.c.C_Ether.v = 100; S.castIste(w, o, 'patlama', null, { x: 0, z: -1 }); adim(w, 2); assert.strictEqual(olen, 2);
});

console.log(sayac + ' test geçti' + (process.exitCode ? ' (HATA VAR)' : ''));
