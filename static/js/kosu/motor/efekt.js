/* Geek Motor · Efekt zinciri (GDevelop efekt mimarisinden esinlenildi: Bloom, ToneMapping, Exposure, HueAndSaturation, Vignette vb.)
   Her efekt adlı bir modüldür: uniform'lar + GLSL parçası. Zincir, açık efektleri sıralayıp TEK bir geçişte birleştirir (mobilde ucuz).
   Çok geçişli efektler (Bloom) kendi hedeflerini 'hazirla' kancasında çizer. three.js yoksa/WebGL2 yoksa zincir kurulmaz (oyun normal çizilir). */
(function (root) {
  'use strict';
  var NS = root.GeekKosu = root.GeekKosu || {};
  var M = NS.motor = NS.motor || {};

  var VERT = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';
  var PARLAK = 'uniform sampler2D tD; uniform vec2 texel; uniform float esik; varying vec2 vUv; void main(){ vec3 c = texture2D(tD, vUv + texel * vec2(-1.0,-1.0)).rgb + texture2D(tD, vUv + texel * vec2(1.0,-1.0)).rgb + texture2D(tD, vUv + texel * vec2(-1.0,1.0)).rgb + texture2D(tD, vUv + texel * vec2(1.0,1.0)).rgb; c *= 0.25; float l = max(c.r, max(c.g, c.b)); float k = smoothstep(esik, esik + 0.55, l); gl_FragColor = vec4(c * k, 1.0); }';
  var BULANIK = 'uniform sampler2D tD; uniform vec2 yon; varying vec2 vUv; void main(){ vec3 c = texture2D(tD, vUv).rgb * 0.2270270; c += (texture2D(tD, vUv + yon * 1.3846154).rgb + texture2D(tD, vUv - yon * 1.3846154).rgb) * 0.3162162; c += (texture2D(tD, vUv + yon * 3.2307692).rgb + texture2D(tD, vUv - yon * 3.2307692).rgb) * 0.0702703; gl_FragColor = vec4(c, 1.0); }';

  /* ---- yerleşik efekt modülleri ---- */
  var TANIM = {};
  TANIM.Hareket = {   // hız bulanıklığı + kenarlarda renk sapması (taban örnekleme)
    sira: 0, taban: true,
    uniforms: { hizR: ['float', 0], aber: ['float', 0], soguk: ['float', 0], merkez: ['vec2', [0.5, 0.46]] },
    glsl: [
      'vec3 fx_taban(vec2 uv, vec2 d, float r){',
      '  vec3 c = vec3(0.0); float a = hizR * 0.05 * smoothstep(0.08, 0.6, r);',
      '  for (int i = 0; i < 6; i++) { float t = float(i) / 5.0; c += texture2D(tS, uv - d * a * t).rgb; }',
      '  c /= 6.0;',
      '  float ab = aber * 0.012 * r + soguk * 0.0025 * r;',
      '  c.r = mix(c.r, texture2D(tS, uv - d * ab * 3.0).r, min(1.0, (aber + soguk) * 2.0));',
      '  c.b = mix(c.b, texture2D(tS, uv + d * ab * 3.0).b, min(1.0, (aber + soguk) * 2.0));',
      '  return c; }'
    ].join('\n')
  };
  TANIM.Bloom = {
    sira: 10, uniforms: { bloom: ['float', 0.55], tB1: ['tex', null], tB2: ['tex', null], esik: ['float', 0.88], esikKayma: ['float', 0] },
    glsl: 'vec3 fx_Bloom(vec3 c, vec2 uv, vec2 d, float r){ return c + bloom * (texture2D(tB1, uv).rgb * 0.7 + texture2D(tB2, uv).rgb * 0.95); }',
    hazirla: function (z, ctx) {
      var p = z.p, m = p.mParlak, b = p.mBulanik, u = z.u;
      m.uniforms.tD.value = p.rt.texture; m.uniforms.texel.value.set(1 / p.rt.width, 1 / p.rt.height); m.uniforms.esik.value = u.esik.value - u.esikKayma.value;
      ctx.gec(m, p.a1);
      b.uniforms.tD.value = p.a1.texture; b.uniforms.yon.value.set(1 / p.a1.width, 0); ctx.gec(b, p.b1);
      b.uniforms.tD.value = p.b1.texture; b.uniforms.yon.value.set(0, 1 / p.a1.height); ctx.gec(b, p.a1);
      b.uniforms.tD.value = p.a1.texture; b.uniforms.yon.value.set(2 / p.a2.width, 0); ctx.gec(b, p.b2);
      b.uniforms.tD.value = p.b2.texture; b.uniforms.yon.value.set(0, 2 / p.a2.height); ctx.gec(b, p.a2);
      b.uniforms.tD.value = p.a2.texture; b.uniforms.yon.value.set(1 / p.a2.width, 0); ctx.gec(b, p.b2);
      b.uniforms.tD.value = p.b2.texture; b.uniforms.yon.value.set(0, 1 / p.a2.height); ctx.gec(b, p.a2);
      u.tB1.value = p.a1.texture; u.tB2.value = p.a2.texture;
    }
  };
  TANIM.GunesIsinlari = {
    sira: 20, uniforms: { gunesUv: ['vec2', [0.7, 0.7]], gunesK: ['float', 0], gunesRenk: ['vec3', [1.0, 0.78, 0.45]], asp: ['float', 1.6] },
    glsl: [
      'vec3 fx_GunesIsinlari(vec3 c, vec2 uv, vec2 d, float r){',
      '  if (gunesK < 0.001) return c;',
      '  vec2 ds = gunesUv - uv; vec3 ray = vec3(0.0); float w = 1.0;',
      '  for (int i = 0; i < 14; i++) { float t = float(i) / 14.0; ray += texture2D(tB1, uv + ds * t * 0.9).rgb * w; w *= 0.93; }',
      '  ray /= 14.0;',
      '  vec2 q = (uv - gunesUv) * vec2(asp, 1.0); float gd = length(q);',
      '  float halo = exp(-gd * 3.2) * 0.55 + exp(-gd * 14.0) * 0.8;',
      '  return c + (ray * 1.25 + gunesRenk * halo) * gunesK; }'
    ].join('\n')
  };
  TANIM.Parlama = {
    sira: 30, uniforms: { flash: ['float', 0] },
    glsl: 'vec3 fx_Parlama(vec3 c, vec2 uv, vec2 d, float r){ return c + vec3(flash); }'
  };
  TANIM.Tonlama = {   // ACES (varsayılan) · Reinhard · Neutral(yumuşak omuz)
    sira: 40, uniforms: { poz: ['float', 0.92], mod: ['float', 0] },
    glsl: [
      'vec3 fx_Tonlama(vec3 c, vec2 uv, vec2 d, float r){',
      '  c *= poz;',
      '  if (mod < 0.5) return clamp((c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14), 0.0, 1.0);',
      '  if (mod < 1.5) return clamp(c / (1.0 + c), 0.0, 1.0);',
      '  vec3 ust = max(c - 0.82, 0.0); return min(c, vec3(0.82)) + 0.18 * (1.0 - exp(-ust / 0.18)); }'
    ].join('\n')
  };
  TANIM.Renk = {      // doygunluk + soğuk/sıcak ton ayrımı (gölge/ışık) + gama
    sira: 50, uniforms: { doygun: ['float', 1.22], soguk: ['float', 0], golgeTon: ['vec3', [0.94, 0.97, 1.08]], isikTon: ['vec3', [1.07, 1.02, 0.93]], gama: ['float', 0.96] },
    glsl: [
      'vec3 fx_Renk(vec3 c, vec2 uv, vec2 d, float r){',
      '  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));',
      '  c = mix(vec3(l), c, doygun - soguk * 0.45);',
      '  c = mix(c, c * vec3(0.78, 0.95, 1.22), soguk);',
      '  c = mix(c * golgeTon, c * isikTon, smoothstep(0.05, 0.85, l));',
      '  return pow(max(c, 0.0), vec3(gama)); }'
    ].join('\n')
  };
  TANIM.Vinyet = {
    sira: 60, uniforms: { vig: ['float', 0.34] },
    glsl: 'vec3 fx_Vinyet(vec3 c, vec2 uv, vec2 d, float r){ float v = smoothstep(1.0, 0.28, r * 1.25); return c * mix(1.0 - vig, 1.0, v); }'
  };
  TANIM.Gren = {
    sira: 70, uniforms: { zaman: ['float', 0], gren: ['float', 0.018] },
    glsl: 'vec3 fx_Gren(vec3 c, vec2 uv, vec2 d, float r){ return c + (fract(sin(dot(uv * 900.0 + zaman, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) * gren; }'
  };

  function tipVec(T, tur, v) {
    if (tur === 'vec2') return new T.Vector2(v[0], v[1]);
    if (tur === 'vec3') return new T.Vector3(v[0], v[1], v[2]);
    return v;
  }

  function Zincir(T, renderer, opts) {
    opts = opts || {};
    this.T = T; this.r = renderer; this.aktifler = []; this.u = {}; this.tanim = {}; this.p = null; this.kok = null; this.hazir = false;
    for (var k in TANIM) this.tanim[k] = TANIM[k];
    this.kuruldu = false;
  }
  var P = Zincir.prototype;
  Zincir.TANIM = TANIM;
  P.tanimla = function (ad, t) { this.tanim[ad] = t; return this; };

  P.kur = function () {
    var T = this.T, r = this.r;
    if (!r.capabilities.isWebGL2) return false;
    var tip = (r.extensions.has('EXT_color_buffer_float') || r.extensions.has('EXT_color_buffer_half_float')) ? T.HalfFloatType : T.UnsignedByteType;
    function hedef(msaa) {
      var rt = new T.WebGLRenderTarget(8, 8, { type: tip, format: T.RGBAFormat, minFilter: T.LinearFilter, magFilter: T.LinearFilter, depthBuffer: !!msaa, samples: msaa ? 4 : 0 });
      rt.texture.generateMipmaps = false; return rt;
    }
    var p = this.p = {
      rt: hedef(true), a1: hedef(false), b1: hedef(false), a2: hedef(false), b2: hedef(false),
      sahne: new T.Scene(), kam: new T.OrthographicCamera(-1, 1, 1, -1, 0, 1)
    };
    p.quad = new T.Mesh(new T.PlaneGeometry(2, 2), null); p.quad.frustumCulled = false; p.sahne.add(p.quad);
    function sm(f, u) { return new T.ShaderMaterial({ vertexShader: VERT, fragmentShader: f, uniforms: u, depthTest: false, depthWrite: false }); }
    p.mParlak = sm(PARLAK, { tD: { value: null }, texel: { value: new T.Vector2() }, esik: { value: 0.88 } });
    p.mBulanik = sm(BULANIK, { tD: { value: null }, yon: { value: new T.Vector2() } });
    this.kuruldu = true; this._derle(); return true;
  };

  P.ekle = function (ad, ayar) {
    var t = this.tanim[ad]; if (!t) throw new Error('Efekt tanımsız: ' + ad);
    if (this.aktifler.indexOf(ad) >= 0) { if (ayar) this.ayarla(ad, ayar); return this; }
    this.aktifler.push(ad);
    for (var k in t.uniforms) if (!this.u[k]) this.u[k] = { value: tipVec(this.T, t.uniforms[k][0], t.uniforms[k][1]) };
    if (ayar) this.ayarla(ad, ayar);
    this.kirli = true; return this;
  };
  P.kaldir = function (ad) { var i = this.aktifler.indexOf(ad); if (i >= 0) { this.aktifler.splice(i, 1); this.kirli = true; } return this; };
  P.acik = function (ad) { return this.aktifler.indexOf(ad) >= 0; };
  P.ayarla = function (ad, ayar, deger) {
    if (typeof ayar === 'string') { var o = {}; o[ayar] = deger; ayar = o; }
    for (var k in ayar) {
      var u = this.u[k]; if (!u) continue;
      var v = ayar[k];
      if (u.value && u.value.set && Array.isArray(v)) u.value.set.apply(u.value, v); else u.value = v;
    }
    return this;
  };

  P._derle = function () {
    var T = this.T, self = this;
    var sirali = this.aktifler.map(function (a) { return a; }).sort(function (a, b) { return self.tanim[a].sira - self.tanim[b].sira; });
    var bild = {}, bildSatir = [];
    sirali.forEach(function (a) {
      var t = self.tanim[a];
      for (var k in t.uniforms) if (!bild[k]) { bild[k] = 1; var tur = t.uniforms[k][0]; bildSatir.push('uniform ' + (tur === 'tex' ? 'sampler2D' : tur) + ' ' + k + ';'); }
    });
    var taban = sirali.filter(function (a) { return self.tanim[a].taban; })[0];
    var govde = ['uniform sampler2D tS;', 'varying vec2 vUv;'].concat(bildSatir);
    sirali.forEach(function (a) { govde.push(self.tanim[a].glsl); });
    if (!bild.merkez) govde.push('const vec2 merkez = vec2(0.5, 0.46);');
    govde.push('void main(){', '  vec2 d = vUv - merkez; float r = length(d);');
    govde.push(taban ? '  vec3 c = fx_taban(vUv, d, r);' : '  vec3 c = texture2D(tS, vUv).rgb;');
    sirali.forEach(function (a) { if (!self.tanim[a].taban) govde.push('  c = fx_' + a + '(c, vUv, d, r);'); });
    govde.push('  gl_FragColor = vec4(max(c, 0.0), 1.0);', '  gl_FragColor = linearToOutputTexel(gl_FragColor);', '}');
    var uni = { tS: { value: null } };
    for (var k in this.u) uni[k] = this.u[k];
    if (this.p.mBirlestir) this.p.mBirlestir.dispose();
    this.p.mBirlestir = new T.ShaderMaterial({ vertexShader: VERT, fragmentShader: govde.join('\n'), uniforms: uni, depthTest: false, depthWrite: false });
    this.kirli = false;
  };

  P.boyutla = function () {
    if (!this.p) return;
    var v = new this.T.Vector2(); this.r.getDrawingBufferSize(v);
    var w = Math.max(2, v.x | 0), h = Math.max(2, v.y | 0), p = this.p;
    p.rt.setSize(w, h);
    p.a1.setSize(Math.max(2, w >> 2), Math.max(2, h >> 2)); p.b1.setSize(p.a1.width, p.a1.height);
    p.a2.setSize(Math.max(2, w >> 3), Math.max(2, h >> 3)); p.b2.setSize(p.a2.width, p.a2.height);
  };
  P.en = function () { return this.p ? this.p.rt.width / this.p.rt.height : 1; };

  P._gec = function (mat, hedef) { var p = this.p; p.quad.material = mat; this.r.setRenderTarget(hedef); this.r.render(p.sahne, p.kam); };

  /* sahneyi çiz → efektleri uygula → ekrana ver. ctx: { dt } */
  P.ciz = function (sahne, kamera, ctx) {
    var self = this, p = this.p;
    if (this.kirli) this._derle();
    this.r.setRenderTarget(p.rt); this.r.render(sahne, kamera);
    var c = { dt: ctx && ctx.dt || 0, gec: function (m, h) { self._gec(m, h); } };
    for (var i = 0; i < this.aktifler.length; i++) { var t = this.tanim[this.aktifler[i]]; if (t.hazirla) t.hazirla(this, c); }
    p.mBirlestir.uniforms.tS.value = p.rt.texture;
    this._gec(p.mBirlestir, null);
  };
  P.at = function () {
    if (!this.p) return; var p = this.p;
    [p.rt, p.a1, p.b1, p.a2, p.b2].forEach(function (x) { x.dispose(); });
    p.mParlak.dispose(); p.mBulanik.dispose(); if (p.mBirlestir) p.mBirlestir.dispose(); this.p = null;
  };

  M.EfektZinciri = Zincir;
})(typeof window !== 'undefined' ? window : globalThis);
