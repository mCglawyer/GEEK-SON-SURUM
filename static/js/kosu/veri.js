/* Geek Oyun · veri katmanı: palet, elementler, yetenekler, düşmanlar. Mantıktan bağımsız, düz veri. */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};

  /* Reia paleti + Geek markası */
  var RENK = {
    yumusakSiyah: '#181a18', yumusakBeyaz: '#fbfaf5', kremBeyaz: '#f9f3e5', sosisSari: '#ffcf0b',
    acikJole: '#1472ba', jole: '#07263d', acikKum: '#d2bc8d', koyuKum: '#bda573',
    hata: '#db2626', basari: '#55dd63', cip: '#558edd', berrakMavi: '#5F9097', ret: '#dd5555',
    geekMavi: '#2a3bd6', geekKrem: '#f2b544', geekLaci: '#0b0f2e'
  };

  /* Elementler (Reia: Pyro / Electro / Hydro) */
  var ELEMENT = {
    pyro:    { ad: 'Kavurma',  renk: 0xff7a2a, css: '#ff7a2a' },
    electro: { ad: 'Elektrik', renk: 0xb26bff, css: '#b26bff' },
    hydro:   { ad: 'Su',       renk: 0x38b6ff, css: '#38b6ff' }
  };
  /* Tepkimeler: iki farklı element üst üste gelince */
  var TEPKIME = {
    'hydro+pyro':     { id: 'buhar',      ad: 'Buhar',      carpan: 1.6 },
    'electro+hydro':  { id: 'sok',        ad: 'Şok Dalgası', carpan: 1.15, sersem: 1.2 },
    'electro+pyro':   { id: 'asiri_yuk',  ad: 'Aşırı Yük',  carpan: 1.0, alan: { r: 3.2, hasar: 16, itme: 7 } }
  };

  /* Yetenekler. kaynak: ether | stamina | yok. mod bazlı ayarlar `mod.<kosu|arena>` ile ezilir. */
  var YETENEK = {
    atis:    { id: 'atis',    ad: 'Kahve Fırlat',     tus: 'Fare', kaynak: 'yok',     maliyet: 0,  cd: 0.42, hasar: 10, hiz: 24, omur: 1.0, r: 0.35, element: null,
               aciklama: 'Yakındaki düşmana otomatik kahve fırlatır.', modlar: ['arena'] },
    dash:    { id: 'dash',    ad: 'Atılma',           tus: 'Shift', kaynak: 'stamina', maliyet: 30, cd: 0.8,  sure: 0.28, hiz: 22, dokunulmaz: 0.34,
               aciklama: 'Kısa süre dokunulmaz ileri atılır. Dayanıklılık harcar.', modlar: ['kosu', 'arena'] },
    top:     { id: 'top',     ad: 'Kavurma Topu',     tus: '1', kaynak: 'ether',   maliyet: 20, cd: 0.55, hasar: 24, hiz: 26, omur: 1.5, r: 0.6, element: 'pyro',
               aciklama: 'Düz giden ateş topu. Kavurma uygular.', modlar: ['kosu', 'arena'] },
    simsek:  { id: 'simsek',  ad: 'Şimşek',           tus: '2', kaynak: 'ether',   maliyet: 32, cd: 2.0,  hasar: 18, menzil: 15, zincir: 3, zincirMenzil: 6.5, element: 'electro',
               aciklama: 'En yakın hedefe çarpar, 3 düşmana kadar zincirlenir.', modlar: ['kosu', 'arena'] },
    firtina: { id: 'firtina', ad: 'Yağmur Fırtınası', tus: '3', kaynak: 'ether',   maliyet: 50, cd: 7.0,  hasar: 6, r: 4.2, sure: 4.5, tick: 0.5, menzil: 11, element: 'hydro',
               aciklama: 'İşaretlenen alanda yağmur yağdırır, ıslatır.', modlar: ['arena'] },
    patlama: { id: 'patlama', ad: 'Patlama',          tus: '4', kaynak: 'ether',   maliyet: 65, cd: 8.0,  hasar: 42, r: 5.0, menzil: 9, itme: 9, element: 'pyro',
               aciklama: 'Hedef noktada büyük alan patlaması.', modlar: ['kosu', 'arena'], mod: { kosu: { r: 7.0, ileri: 8 } } },
    kalkan:  { id: 'kalkan',  ad: 'Köpük Kalkan',     tus: 'Q', kaynak: 'ether',   maliyet: 30, cd: 10.0, emilim: 60, sure: 7,
               aciklama: 'Gelen hasarın bir kısmını emen köpük kalkan.', modlar: ['kosu', 'arena'] }
  };
  var YETENEK_SIRA = ['top', 'simsek', 'firtina', 'patlama', 'kalkan', 'dash'];

  /* Düşmanlar (Reia: slime / king slime / goblin → Geek temalı) */
  var DUSMAN = {
    jole:   { id: 'jole',   ad: 'Süt Jölesi',       can: 42,  hiz: 3.3, r: 0.75, temas: 10, temasBekle: 0.9, puan: 10, aggro: 15, ether: 7,  tip: 'slime',
              not: 'Zıplayarak kovalar, temasla hasar verir.' },
    goblin: { id: 'goblin', ad: 'Kruvasan Goblini', can: 78,  hiz: 4.3, r: 0.65, hasar: 15, menzil: 1.7, bekle: 1.15, hazirlik: 0.42, puan: 25, aggro: 15, ether: 10, tip: 'goblin',
              not: 'Hızlı koşar; vurmadan önce kısa süre hazırlanır.' },
    kral:   { id: 'kral',   ad: 'Kral Jöle',        can: 650, hiz: 2.2, r: 1.9,  temas: 18, temasBekle: 1.0, puan: 300, aggro: 40, ether: 40, tip: 'kral', boss: true,
              vurusAralik: 6.0, vurusHazirlik: 0.95, vurusR: 5.6, vurusHasar: 24,
              not: 'Yere vurarak alan hasarı verir; canı azaldıkça jöle doğurur.' }
  };

  /* Tuş etiketleri (moda göre numaralar yeniden sıralanır) ve eylem çubuğu sırası */
  var TUS = {
    kosu:  { sira: ['top', 'simsek', 'patlama', 'kalkan', 'dash'], tus: { top: '1', simsek: '2', patlama: '3', kalkan: 'Q', dash: '⇧' }, kod: { Digit1: 'top', Digit2: 'simsek', Digit3: 'patlama', KeyQ: 'kalkan', ShiftLeft: 'dash', ShiftRight: 'dash' } },
    arena: { sira: ['top', 'simsek', 'firtina', 'patlama', 'kalkan', 'dash'], tus: { top: '1', simsek: '2', firtina: '3', patlama: '4', kalkan: 'Q', dash: '⇧' }, kod: { Digit1: 'top', Digit2: 'simsek', Digit3: 'firtina', Digit4: 'patlama', KeyQ: 'kalkan', ShiftLeft: 'dash', ShiftRight: 'dash', Space: 'dash' } }
  };

  var NS_VERI = { TUS: TUS, RENK: RENK, ELEMENT: ELEMENT, TEPKIME: TEPKIME, YETENEK: YETENEK, YETENEK_SIRA: YETENEK_SIRA, DUSMAN: DUSMAN };
  NS_VERI.yetenek = function (id, mod) {
    var y = YETENEK[id]; if (!y) return null;
    var o = {}, k;
    for (k in y) o[k] = y[k];
    if (y.mod && y.mod[mod]) for (k in y.mod[mod]) o[k] = y.mod[mod][k];
    return o;
  };
  NS.veri = NS_VERI;
  if (typeof module !== 'undefined' && module.exports) module.exports = NS;
})(typeof window !== 'undefined' ? window : globalThis);
