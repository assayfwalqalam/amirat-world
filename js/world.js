/* Amiratu al-Ulum · the open world
   Engine: streaming terrain, biomes, water, vegetation, physics, fire, sky. */
(function () {
  'use strict';

  var W = window.W = {};

  /* ---------------------------------------------------------------- diag */
  var msgs = [];
  W.diag = function (m) {
    msgs.push(String(m).slice(0, 140));
    if (msgs.length > 3) msgs.shift();
    var d = document.getElementById('diag');
    if (d) { d.style.display = 'block'; d.textContent = msgs.join('  ·  '); }
  };
  window.addEventListener('error', function (e) { W.diag('ERR ' + (e.message || e.type) + ' @' + (e.lineno || '?')); });
  window.addEventListener('unhandledrejection', function (e) {
    var m = String((e.reason && e.reason.message) || e.reason || '');
    if (m.indexOf('ointerLock') >= 0 || m.indexOf('pointer lock') >= 0) { e.preventDefault(); return; }
    W.diag('REJ ' + m);
  });
  (function () {
    var ce = console.error;
    console.error = function () {
      try { W.diag('E ' + Array.prototype.join.call(arguments, ' ').slice(0, 130)); } catch (x) {}
      return ce.apply(console, arguments);
    };
  })();

  /* --------------------------------------------------------------- noise */
  function hash2(x, y) {
    var n = Math.sin(x * 127.1 + y * 311.7) * 43758.5453123;
    return n - Math.floor(n);
  }
  function noise2(x, y) {
    var xi = Math.floor(x), yi = Math.floor(y);
    var xf = x - xi, yf = y - yi;
    var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    var a = hash2(xi, yi), b = hash2(xi + 1, yi), c = hash2(xi, yi + 1), d = hash2(xi + 1, yi + 1);
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v;
  }
  function fbm(x, y, oct) {
    var s = 0, a = 0.5, f = 1, n = 0;
    for (var i = 0; i < oct; i++) { s += noise2(x * f, y * f) * a; n += a; a *= 0.5; f *= 2; }
    return s / n;
  }
  function ridged(x, y, oct) {
    var s = 0, a = 0.5, f = 1, n = 0;
    for (var i = 0; i < oct; i++) { s += (1 - Math.abs(noise2(x * f, y * f) * 2 - 1)) * a; n += a; a *= 0.5; f *= 2; }
    return s / n;
  }
  function sstep(e0, e1, x) { var t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  W.noise2 = noise2; W.fbm = fbm; W.hash2 = hash2; W.sstep = sstep;

  /* ------------------------------------------------------- world shaping */
  var WATER_Y = 0;
  W.WATER_Y = WATER_Y;

  /* places that flatten the land beneath them */
  var FLATS = [];
  W.addFlat = function (x, z, r, y, blend) { FLATS.push({ x: x, z: z, r: r, y: y, b: blend || 40 }); };

  function riverAt(x, z) {
    var r = ridged(x * 0.00085 + 4.1, z * 0.00085 - 2.7, 3);
    return sstep(0.955, 1.0, r);
  }
  function lakeAt(x, z) {
    var l = fbm(x * 0.00062 - 88.3, z * 0.00062 + 12.9, 3);
    return sstep(0.70, 0.80, l);
  }

  W.biomeAt = function (x, z) {
    var moist = fbm(x * 0.00040 + 91.3, z * 0.00040 - 17.7, 3);
    var rocky = fbm(x * 0.00066 - 33.1, z * 0.00066 + 55.9, 3);
    var g = sstep(0.44, 0.62, moist);
    var r = sstep(0.56, 0.73, rocky) * (1 - g * 0.8);
    return { grass: g, rock: r };
  };

  W.heightAt = function (x, z) {
    var b = W.biomeAt(x, z);
    /* the land rides above the water table · only carved basins flood */
    var cont = fbm(x * 0.00055, z * 0.00055, 4);
    var h = (cont - 0.13) * 165;

    /* dunes ride on a warped field so their crests wander instead of marching */
    var wx = x + fbm(x * 0.0013 + 21.4, z * 0.0013 - 8.2, 2) * 260;
    var wz = z + fbm(x * 0.0011 - 5.6, z * 0.0011 + 14.9, 2) * 260;
    var dune = ridged(wx * 0.0040 + 7.7, wz * 0.0034 - 3.3, 3);
    var dune2 = ridged(wx * 0.0011 - 2.2, wz * 0.0013 + 5.5, 2);
    h += ((dune - 0.5) * 16 + (dune2 - 0.5) * 21) * (1 - b.grass) * (1 - b.rock * 0.7);

    var hill = fbm(x * 0.0021 - 12.5, z * 0.0021 + 8.8, 4);
    h += Math.pow(Math.max(0, hill), 1.9) * 165 * b.rock;

    h += (fbm(x * 0.0065, z * 0.0065, 3) - 0.5) * 9 * b.grass;
    h += (fbm(x * 0.021, z * 0.021, 2) - 0.5) * 2.2;

    var low = sstep(46, 5, h);
    var riv = riverAt(x, z) * low;
    h = lerp(h, WATER_Y - 3.4, riv);

    var lk = lakeAt(x, z) * sstep(60, 10, h);
    h = lerp(h, WATER_Y - 4.6, lk);

    for (var i = 0; i < FLATS.length; i++) {
      var f = FLATS[i];
      var d = Math.sqrt((x - f.x) * (x - f.x) + (z - f.z) * (z - f.z));
      h = lerp(f.y, h, sstep(f.r, f.r + f.b, d));
    }
    return h;
  };

  /* wetness/greenery weights used by the ground shader and the scatterer */
  W.groundWeights = function (x, z, h) {
    var b = W.biomeAt(x, z);
    var wet = sstep(16.0, 0.2, h - WATER_Y);
    var grass = Math.min(1, Math.max(b.grass, wet * 0.92));
    var rock = Math.min(1, b.rock * 0.9 + sstep(120, 190, h) * 0.7);
    return { g: grass, r: rock, w: wet };
  };

  /* --------------------------------------------------------------- boot */
  var renderer, scene, cam, clock;
  var LOWQ = false;
  try { LOWQ = sessionStorage.getItem('lowq') === '1'; } catch (e) {}

  /* small screens and modest devices get a lighter world, automatically */
  var mem = navigator.deviceMemory || 4;
  var small = Math.min(innerWidth, innerHeight) < 560 || 'ontouchstart' in window;
  var TIER = LOWQ ? 0 : (small || mem < 4 ? 1 : 2);
  W.TIER = TIER;
  W.vegScale = TIER === 2 ? 1 : (TIER === 1 ? 0.55 : 0.3);

  W.start = function () {
    try {
      renderer = new THREE.WebGLRenderer({ antialias: !LOWQ, powerPreference: 'high-performance' });
    } catch (err) { W.diag('WebGL unavailable: ' + err.message); return; }
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(TIER === 2 ? Math.min(devicePixelRatio, 1.9) : (TIER === 1 ? Math.min(devicePixelRatio, 1.5) : 1));
    renderer.setClearColor(0x0a0916);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.95;
    renderer.shadowMap.enabled = false;
    document.body.appendChild(renderer.domElement);
    renderer.domElement.addEventListener('webglcontextlost', function (ev) {
      ev.preventDefault();
      var once = false;
      try { if (sessionStorage.getItem('lowq') !== '1') { sessionStorage.setItem('lowq', '1'); once = true; } } catch (e) {}
      if (once) location.reload(); else W.diag('graphics context lost · reopen the page');
    });
    setTimeout(function () { try { sessionStorage.removeItem('lowq'); } catch (e) {} }, 20000);

    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x1d1937, 0.00105);
    cam = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.12, 6000);
    clock = new THREE.Clock();
    W.scene = scene; W.cam = cam; W.renderer = renderer;

    initSky();
    initGround();
    initWater();
    initLights();
    if (W.buildAll) W.buildAll(W);
    initPlayer();
    startLoop();
  };

  /* ---------------------------------------------------------------- tex */
  var texWaits = [];
  function tex(url, srgb, rep) {
    var t = new THREE.TextureLoader().load(url,
      function () { t.needsUpdate = true; },
      undefined,
      function () { W.diag('texture failed: ' + url); });
    t.encoding = srgb ? THREE.sRGBEncoding : THREE.LinearEncoding;
    if (rep) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
    t.anisotropy = LOWQ ? 1 : 8;
    return t;
  }
  W.tex = tex;

  /* ---------------------------------------------------------------- sky */
  var moonMesh, halo, clouds = [], moonDir;
  function initSky() {
    var sky = tex('assets/puresky_4k.jpg', true);
    sky.mapping = THREE.EquirectangularReflectionMapping;
    scene.background = sky;

    moonDir = new THREE.Vector3(0.36, 0.42, -0.83).normalize();
    var mp = moonDir.clone().multiplyScalar(2600);

    halo = new THREE.Mesh(new THREE.PlaneGeometry(1150, 1150),
      new THREE.MeshBasicMaterial({ map: tex('assets/glow.png', true), color: 0xa9b6f0, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, toneMapped: false, opacity: 0.5 }));
    halo.position.copy(mp); scene.add(halo);

    moonMesh = new THREE.Mesh(new THREE.PlaneGeometry(310, 310),
      new THREE.MeshBasicMaterial({ map: tex('assets/moon.png', true), transparent: true, depthWrite: false, fog: false, toneMapped: false }));
    moonMesh.position.copy(mp); scene.add(moonMesh);

    var ctex = [tex('assets/cloud0.png', true), tex('assets/cloud1.png', true), tex('assets/cloud2.png', true)];
    var defs = [
      { az: 0.4, el: 0.42, r: 2300, w: 1500, o: 0.5, sp: 0.0036 },
      { az: 1.7, el: 0.28, r: 2200, w: 1250, o: 0.4, sp: 0.0028 },
      { az: 3.1, el: 0.35, r: 2400, w: 1400, o: 0.34, sp: 0.0042 },
      { az: 4.6, el: 0.22, r: 2150, w: 1050, o: 0.3, sp: 0.0031 },
      { az: 5.6, el: 0.40, r: 2350, w: 1300, o: 0.28, sp: 0.0039 }
    ];
    defs.forEach(function (d, i) {
      var m = new THREE.Mesh(new THREE.PlaneGeometry(d.w, d.w * 0.5),
        new THREE.MeshBasicMaterial({ map: ctex[i % 3], color: 0xc0c2e0, transparent: true, depthWrite: false, fog: false, opacity: d.o }));
      m.renderOrder = 2; scene.add(m);
      clouds.push({ m: m, az: d.az, el: d.el, r: d.r, sp: d.sp });
    });

    /* bright foreground stars over the photographed sky */
    function stars(n, size, op) {
      var g = new THREE.BufferGeometry(), p = new Float32Array(n * 3);
      for (var i = 0; i < n; i++) {
        var az = Math.random() * Math.PI * 2, el = 0.05 + Math.random() * 1.4, r = 2700;
        p[i * 3] = r * Math.cos(el) * Math.cos(az);
        p[i * 3 + 1] = r * Math.sin(el);
        p[i * 3 + 2] = r * Math.cos(el) * Math.sin(az);
      }
      g.setAttribute('position', new THREE.BufferAttribute(p, 3));
      return new THREE.Points(g, new THREE.PointsMaterial({ color: 0xf4f1e6, size: size, sizeAttenuation: false, transparent: true, opacity: op, fog: false, depthWrite: false }));
    }
    scene.add(stars(500, 1.7, 0.6));
    scene.add(stars(90, 2.7, 0.85));
  }

  function skyFollow(p) {
    var g = new THREE.Group();
    clouds.forEach(function (c) {
      var y = Math.sin(c.el) * c.r, rr = Math.cos(c.el) * c.r;
      c.m.position.set(p.x + Math.cos(c.az) * rr, y, p.z + Math.sin(c.az) * rr);
      c.m.lookAt(p.x, p.y, p.z);
    });
    var mp = moonDir.clone().multiplyScalar(2600).add(new THREE.Vector3(p.x, 0, p.z));
    moonMesh.position.copy(mp); moonMesh.lookAt(p);
    halo.position.copy(mp); halo.lookAt(p);
  }

  /* ------------------------------------------------------------- lights */
  function initLights() {
    /* moonlight from above, and the whole sky as a soft fill · nothing reads pure black */
    scene.add(new THREE.HemisphereLight(0x6a6cb4, 0x2b2540, 0.85));
    scene.add(new THREE.AmbientLight(0x3b3a63, 0.30));
    var moon = new THREE.DirectionalLight(0xccd2ff, 0.88);
    moon.position.copy(moonDir).multiplyScalar(900);
    scene.add(moon);
  }

  /* ------------------------------------------------------------- ground */
  var groundMat;
  function initGround() {
    var tSand = tex('assets/g_sand_d.jpg', true, true);
    var tGrav = tex('assets/g_gravel_d.jpg', true, true);
    var tRock = tex('assets/g_rock_d.jpg', true, true);
    var tGrass = tex('assets/g_grass_d.jpg', true, true);
    var tMask = tex('assets/g_crack_d.jpg', false, true);

    groundMat = new THREE.MeshStandardMaterial({
      color: 0xffffff, roughness: 0.97, metalness: 0.0,
      vertexColors: true, side: THREE.FrontSide
    });
    groundMat.onBeforeCompile = function (sh) {
      sh.uniforms.tSand = { value: tSand };
      sh.uniforms.tGrav = { value: tGrav };
      sh.uniforms.tRock = { value: tRock };
      sh.uniforms.tGrass = { value: tGrass };
      sh.uniforms.tMask = { value: tMask };

      sh.vertexShader = 'varying vec3 vWPos;\nvarying vec3 vWNrm;\n' + sh.vertexShader.replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\n vWPos = (modelMatrix * vec4(transformed,1.0)).xyz;\n vWNrm = normalize(mat3(modelMatrix) * objectNormal);'
      );

      sh.fragmentShader = 'uniform sampler2D tSand;\nuniform sampler2D tGrav;\nuniform sampler2D tRock;\nuniform sampler2D tGrass;\nuniform sampler2D tMask;\nvarying vec3 vWPos;\nvarying vec3 vWNrm;\n' + sh.fragmentShader;
      /* vertex colours carry biome weights, so do not tint by them */
      sh.fragmentShader = sh.fragmentShader.replace('#include <color_fragment>', '');
      sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>',
        [
          'vec2 wxz = vWPos.xz;',
          'float macro = texture2D(tMask, wxz * 0.00225).r;',
          'float macro2 = texture2D(tMask, wxz * 0.00072 + vec2(0.37, 0.11)).r;',
          'float fine  = texture2D(tMask, wxz * 0.0195 + vec2(0.8, 0.3)).r;',
          /* sand: two different photos at two scales, mixed by a large organic mask */
          'vec3 sA = texture2D(tSand, wxz * 0.085).rgb;',
          'vec3 sB = texture2D(tGrav, wxz * 0.052).rgb;',
          'vec3 sC = texture2D(tSand, wxz * 0.0143).rgb;',
          'vec3 sand = mix(sA, sB, smoothstep(0.40, 0.66, macro));',
          'sand *= (0.62 + 0.82 * sC.r) * (0.80 + 0.42 * macro2);',
          /* rock */
          'vec3 rA = texture2D(tRock, wxz * 0.062).rgb;',
          'vec3 rB = texture2D(tRock, wxz * 0.0121 + vec2(0.5)).rgb;',
          'vec3 rock = rA * (0.66 + 0.78 * rB.r);',
          /* grass */
          'vec3 gA = texture2D(tGrass, wxz * 0.098).rgb;',
          'vec3 gB = texture2D(tGrass, wxz * 0.0172 + vec2(0.2, 0.7)).rgb;',
          'vec3 grass = gA * (0.60 + 0.85 * gB.g);',
          'grass *= (0.86 + 0.30 * macro);',
          'float slope = 1.0 - clamp(vWNrm.y, 0.0, 1.0);',
          'float wRock = clamp(vColor.g + smoothstep(0.30, 0.62, slope) - 0.10 * vColor.r, 0.0, 1.0);',
          'vec3 col = mix(sand, grass, clamp(vColor.r * (0.85 + 0.3 * fine), 0.0, 1.0));',
          'col = mix(col, rock, wRock);',
          'col = mix(col, col * vec3(0.70, 0.76, 0.70), vColor.b * 0.55);',
          'col *= 0.94 + 0.12 * fine;',
          'diffuseColor.rgb *= col;'
        ].join('\n'));
    };
    W.groundMat = groundMat;
  }

  /* --------------------------------------------------- terrain chunking */
  var CH = 192;
  var RINGS = TIER === 2 ? [
    { r: 1, seg: 44 }, { r: 2, seg: 22 }, { r: 3, seg: 12 },
    { r: 4, seg: 8 }, { r: 6, seg: 5 }, { r: 9, seg: 3 }
  ] : TIER === 1 ? [
    { r: 1, seg: 32 }, { r: 2, seg: 16 }, { r: 3, seg: 9 }, { r: 5, seg: 5 }, { r: 7, seg: 3 }
  ] : [
    { r: 1, seg: 24 }, { r: 2, seg: 12 }, { r: 4, seg: 6 }, { r: 6, seg: 3 }
  ];
  var VEG_SEG = TIER === 2 ? 22 : (TIER === 1 ? 16 : 999);
  var chunks = new Map();
  var pending = [];

  function segFor(di, dj) {
    var d = Math.max(Math.abs(di), Math.abs(dj));
    for (var i = 0; i < RINGS.length; i++) if (d <= RINGS[i].r) return RINGS[i].seg;
    return 0;
  }

  function buildChunkGeo(ox, oz, size, seg) {
    var n = seg + 1;
    var pos = [], col = [], idx = [], nrm = [];
    var H = new Float32Array(n * n);
    var q = size / seg;
    for (var j = 0; j < n; j++) {
      for (var i = 0; i < n; i++) {
        var x = ox + (i / seg) * size;
        var z = oz + (j / seg) * size;
        var y = W.heightAt(x, z);
        H[j * n + i] = y;
        pos.push(x - ox, y, z - oz);
        var w = W.groundWeights(x, z, y);
        col.push(w.g, w.r, w.w);
      }
    }
    /* normals straight from the heightfield · identical shading at every detail level */
    for (var j5 = 0; j5 < n; j5++) {
      for (var i5 = 0; i5 < n; i5++) {
        var xm = H[j5 * n + Math.max(0, i5 - 1)], xp = H[j5 * n + Math.min(n - 1, i5 + 1)];
        var zm = H[Math.max(0, j5 - 1) * n + i5], zp = H[Math.min(n - 1, j5 + 1) * n + i5];
        var sx = (i5 === 0 || i5 === n - 1) ? q : 2 * q;
        var sz = (j5 === 0 || j5 === n - 1) ? q : 2 * q;
        var nx = (xm - xp) / sx, nz = (zm - zp) / sz;
        var len = Math.sqrt(nx * nx + 1 + nz * nz);
        nrm.push(nx / len, 1 / len, nz / len);
      }
    }
    for (var j2 = 0; j2 < seg; j2++) {
      for (var i2 = 0; i2 < seg; i2++) {
        var a = j2 * n + i2, b = a + 1, d = a + n, e = d + 1;
        idx.push(a, d, b, b, d, e);
      }
    }
    /* skirt: a curtain around the border so LOD seams cannot show daylight */
    var border = [];
    for (var i3 = 0; i3 < seg; i3++) border.push(i3);
    for (var j3 = 0; j3 < seg; j3++) border.push(j3 * n + seg);
    for (var i4 = seg; i4 > 0; i4--) border.push(seg * n + i4);
    for (var j4 = seg; j4 > 0; j4--) border.push(j4 * n);
    /* the skirt hides LOD seams · pulled inward and kept shallow so it never
       shows itself, and its normals point up so it shades like the ground */
    var skirtStart = pos.length / 3;
    var cxm = size / 2, czm = size / 2;
    for (var k = 0; k < border.length; k++) {
      var bi = border[k];
      var bx = pos[bi * 3], bz = pos[bi * 3 + 2];
      var ix = bx + (cxm - bx) * 0.10, iz = bz + (czm - bz) * 0.10;
      pos.push(ix, pos[bi * 3 + 1] - 9, iz);
      col.push(col[bi * 3], col[bi * 3 + 1], col[bi * 3 + 2]);
      nrm.push(nrm[bi * 3], nrm[bi * 3 + 1], nrm[bi * 3 + 2]);
    }
    for (var k2 = 0; k2 < border.length; k2++) {
      var b0 = border[k2], b1 = border[(k2 + 1) % border.length];
      var s0 = skirtStart + k2, s1 = skirtStart + ((k2 + 1) % border.length);
      idx.push(b0, s0, b1, b1, s0, s1);
    }
    var g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
    g.setIndex(idx);
    g.computeBoundingSphere();
    return g;
  }

  function makeChunk(ci, cj, seg) {
    var ox = ci * CH, oz = cj * CH;
    var geo = buildChunkGeo(ox, oz, CH, seg);
    var m = new THREE.Mesh(geo, groundMat);
    m.position.set(ox, 0, oz);
    m.frustumCulled = true;
    scene.add(m);
    var rec = { mesh: m, seg: seg, veg: null, ci: ci, cj: cj };
    if (seg >= VEG_SEG && W.scatter) rec.veg = W.scatter(W, ci, cj, CH, seg);
    return rec;
  }

  function disposeChunk(rec) {
    scene.remove(rec.mesh);
    rec.mesh.geometry.dispose();
    if (rec.veg) {
      for (var i = 0; i < rec.veg.length; i++) {
        var v = rec.veg[i];
        scene.remove(v);
        if (v.dispose) v.dispose();
        if (v.userData && v.userData.col) W.removeBox(v.userData.col);
      }
    }
  }

  /* re-sow every loaded chunk once the models have arrived */
  W.refreshVeg = function () {
    chunks.forEach(function (rec) {
      if (rec.veg) {
        for (var i = 0; i < rec.veg.length; i++) {
          var v = rec.veg[i];
          scene.remove(v);
          if (v.dispose) v.dispose();
          if (v.userData && v.userData.col) W.removeBox(v.userData.col);
        }
        rec.veg = null;
      }
      if (rec.seg >= VEG_SEG && W.scatter) rec.veg = W.scatter(W, rec.ci, rec.cj, CH, rec.seg);
    });
  };

  var lastCi = 1e9, lastCj = 1e9;
  function updateChunks(p, force) {
    var ci = Math.floor(p.x / CH), cj = Math.floor(p.z / CH);
    if (!force && ci === lastCi && cj === lastCj) return;
    lastCi = ci; lastCj = cj;
    var maxR = RINGS[RINGS.length - 1].r;
    var want = new Set();
    for (var dj = -maxR; dj <= maxR; dj++) {
      for (var di = -maxR; di <= maxR; di++) {
        var seg = segFor(di, dj);
        if (!seg) continue;
        var key = (ci + di) + ',' + (cj + dj);
        want.add(key);
        var have = chunks.get(key);
        if (have && have.seg === seg) continue;
        pending.push({ key: key, ci: ci + di, cj: cj + dj, seg: seg, d: Math.abs(di) + Math.abs(dj) });
      }
    }
    chunks.forEach(function (rec, key) {
      if (!want.has(key)) { disposeChunk(rec); chunks.delete(key); }
    });
    pending.sort(function (a, b) { return a.d - b.d; });
  }

  function pumpChunks(budget) {
    var made = 0;
    while (pending.length && made < budget) {
      var job = pending.shift();
      var old = chunks.get(job.key);
      if (old && old.seg === job.seg) continue;
      if (old) { disposeChunk(old); chunks.delete(job.key); }
      chunks.set(job.key, makeChunk(job.ci, job.cj, job.seg));
      made++;
    }
  }

  /* -------------------------------------------------------------- water */
  var water;
  function initWater() {
    var wn = tex('assets/water_n.jpg', false, true);
    wn.repeat.set(120, 120);
    var g = new THREE.PlaneGeometry(7000, 7000, 1, 1);
    g.rotateX(-Math.PI / 2);
    var m = new THREE.MeshStandardMaterial({
      color: 0x16203c, roughness: 0.14, metalness: 0.55,
      normalMap: wn, normalScale: new THREE.Vector2(0.5, 0.5),
      transparent: true, opacity: 0.93
    });
    water = new THREE.Mesh(g, m);
    water.position.y = WATER_Y;
    water.renderOrder = 1;
    scene.add(water);
    W.water = water;
  }

  /* ------------------------------------------------------------ physics */
  var COLL = [];          /* oriented boxes */
  var GRID = new Map();   /* spatial hash */
  var CELL = 26;
  function cellKey(x, z) { return Math.floor(x / CELL) + ',' + Math.floor(z / CELL); }

  W.addBox = function (cx, cy, cz, hx, hy, hz, rot) {
    var b = { cx: cx, cz: cz, hx: hx, hz: hz, y0: cy - hy, y1: cy + hy, rot: rot || 0,
              c: Math.cos(rot || 0), s: Math.sin(rot || 0) };
    COLL.push(b);
    var reach = Math.sqrt(hx * hx + hz * hz) + CELL;
    for (var x = cx - reach; x <= cx + reach; x += CELL) {
      for (var z = cz - reach; z <= cz + reach; z += CELL) {
        var k = cellKey(x, z);
        var a = GRID.get(k);
        if (!a) { a = []; GRID.set(k, a); }
        if (a.indexOf(b) < 0) a.push(b);
      }
    }
    return b;
  };
  /* colliders that belong to streamed chunks go away with them */
  W.removeBox = function (b) { if (b) b.dead = true; };
  W.nearBoxes = function (x, z) {
    var out = [], seen = {};
    for (var dx = -1; dx <= 1; dx++) {
      for (var dz = -1; dz <= 1; dz++) {
        var a = GRID.get(cellKey(x + dx * CELL, z + dz * CELL));
        if (!a) continue;
        for (var i = 0; i < a.length; i++) {
          var b = a[i];
          if (!seen[b.cx + '_' + b.cz + '_' + b.y0]) { seen[b.cx + '_' + b.cz + '_' + b.y0] = 1; out.push(b); }
        }
      }
    }
    return out;
  };

  /* ------------------------------------------------------------- player */
  var PR = 0.42, PH = 1.72, STEP = 0.62, GRAV = -23.5, JUMP = 8.4;
  var pos = new THREE.Vector3(), vel = new THREE.Vector3();
  var yaw = 0, pitch = -0.04, fly = false, grounded = false;
  var keys = {}, moveVec = { x: 0, y: 0 }, movePid = null, moveOrigin = null, looks = {};
  var plBlocked = false;
  var startEl, stickEl, stickN;
  W.getPos = function () { return pos; };
  W.getYaw = function () { return yaw; };

  function initPlayer() {
    var s = (W.SPAWN || { x: 0, z: 150 });
    pos.set(s.x, W.heightAt(s.x, s.z) + PH + 0.4, s.z);
    yaw = (W.SPAWN_YAW !== undefined) ? W.SPAWN_YAW : Math.PI;

    /* fixed viewpoints, for inspecting the world */
    var q = new URLSearchParams(location.search);
    var shot = q.get('shot');
    if (shot) {
      var P = W.SHOTS && W.SHOTS[shot];
      if (P) {
        pos.set(P.x, W.heightAt(P.x, P.z) + (P.h || PH), P.z);
        yaw = P.yaw; pitch = P.pitch || -0.05;
        if (P.fly) fly = true;
      }
      var so = document.getElementById('start');
      if (so) so.classList.add('off');
      W.setIdle(1e9);
    }

    startEl = document.getElementById('start');
    stickEl = document.getElementById('stick');
    stickN = document.getElementById('stickn');
    var canvas = renderer.domElement;

    function lock() {
      if (plBlocked || 'ontouchstart' in window) return;
      try {
        var p = canvas.requestPointerLock && canvas.requestPointerLock();
        if (p && p.catch) p.catch(function () { plBlocked = true; });
      } catch (e) { plBlocked = true; }
    }
    if (startEl) startEl.addEventListener('click', function () { startEl.classList.add('off'); lock(); wake(); });
    canvas.addEventListener('click', function () { lock(); wake(); });

    document.addEventListener('mousemove', function (e) {
      if (document.pointerLockElement !== canvas) return;
      yaw -= e.movementX * 0.0021; pitch -= e.movementY * 0.0021;
      pitch = Math.max(-1.35, Math.min(1.35, pitch));
      wake();
    });
    canvas.addEventListener('pointerdown', function (e) {
      wake();
      if (document.pointerLockElement === canvas) return;
      if (e.clientX < innerWidth * 0.42 && movePid === null) {
        movePid = e.pointerId; moveOrigin = { x: e.clientX, y: e.clientY };
        stickEl.style.display = 'block';
        stickEl.style.left = (e.clientX - 55) + 'px';
        stickEl.style.top = (e.clientY - 55) + 'px';
        stickN.style.transform = 'translate(0,0)';
      } else {
        looks[e.pointerId] = { x: e.clientX, y: e.clientY };
      }
    });
    addEventListener('pointermove', function (e) {
      if (e.pointerId === movePid && moveOrigin) {
        if (e.cancelable) e.preventDefault();
        var dx = e.clientX - moveOrigin.x, dy = e.clientY - moveOrigin.y;
        var m = Math.hypot(dx, dy), cap = 52;
        if (m > cap) { dx *= cap / m; dy *= cap / m; }
        moveVec.x = dx / cap; moveVec.y = dy / cap;
        stickN.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
        wake();
      } else if (looks[e.pointerId]) {
        if (e.cancelable) e.preventDefault();
        var l = looks[e.pointerId];
        yaw -= (e.clientX - l.x) * 0.0034; pitch -= (e.clientY - l.y) * 0.0034;
        pitch = Math.max(-1.35, Math.min(1.35, pitch));
        l.x = e.clientX; l.y = e.clientY;
        wake();
      }
    }, { passive: false });
    function endPtr(e) {
      if (e.pointerId === movePid) { movePid = null; moveOrigin = null; moveVec.x = moveVec.y = 0; stickEl.style.display = 'none'; }
      delete looks[e.pointerId];
    }
    addEventListener('pointerup', endPtr);
    addEventListener('pointercancel', endPtr);

    document.addEventListener('keydown', function (e) {
      keys[e.code] = true; wake();
      if (e.code === 'KeyF') { fly = !fly; setMode(); }
      if (e.code === 'KeyE' && W.interact) W.interact(W);
      if (e.code === 'Space' && e.target === document.body) e.preventDefault();
    });
    document.addEventListener('keyup', function (e) { keys[e.code] = false; });

    function setMode() {
      var a = document.getElementById('cWalk'), b = document.getElementById('cFly');
      if (a) a.classList.toggle('on', !fly);
      if (b) b.classList.toggle('on', fly);
    }
    var cw = document.getElementById('cWalk'), cf = document.getElementById('cFly');
    if (cw) cw.addEventListener('click', function () { fly = false; setMode(); wake(); });
    if (cf) cf.addEventListener('click', function () { fly = true; setMode(); wake(); });
    var cj = document.getElementById('cJump');
    if (cj) cj.addEventListener('click', function () { tryJump(); wake(); });
    var ca = document.getElementById('actChip');
    if (ca) ca.addEventListener('click', function () { if (W.interact) W.interact(W); wake(); });
    setMode();
    updateChunks(pos, true);
    pumpChunks(60);
  }

  function tryJump() { if (grounded && !fly) { vel.y = JUMP; grounded = false; } }

  function resolve(p) {
    var boxes = W.nearBoxes(p.x, p.z);
    var feet = p.y - PH, head = p.y;
    for (var i = 0; i < boxes.length; i++) {
      var b = boxes[i];
      if (b.dead || head < b.y0 || feet > b.y1) continue;
      var dx = p.x - b.cx, dz = p.z - b.cz;
      var lx = dx * b.c + dz * b.s;
      var lz = -dx * b.s + dz * b.c;
      var ox = b.hx + PR - Math.abs(lx);
      var oz = b.hz + PR - Math.abs(lz);
      if (ox <= 0 || oz <= 0) continue;
      /* stand on top when the ledge is a step's height away */
      if (b.y1 - feet <= STEP && b.y1 - feet > -0.05 && vel.y <= 0.01) {
        p.y = b.y1 + PH; vel.y = 0; grounded = true; continue;
      }
      if (ox < oz) { lx += (lx > 0 ? ox : -ox); } else { lz += (lz > 0 ? oz : -oz); }
      p.x = b.cx + lx * b.c - lz * b.s;
      p.z = b.cz + lx * b.s + lz * b.c;
    }
  }

  function step(dt) {
    var sp = fly ? 42 : (keys['ShiftLeft'] || keys['ShiftRight'] ? 17 : 9.2);
    var f = new THREE.Vector3(Math.sin(yaw), 0, Math.cos(yaw)).multiplyScalar(-1);
    if (fly) { f.y = Math.sin(pitch); f.normalize(); }
    var r = new THREE.Vector3(-f.z, 0, f.x).normalize();
    var wish = new THREE.Vector3();
    if (keys['KeyW'] || keys['ArrowUp']) wish.add(f);
    if (keys['KeyS'] || keys['ArrowDown']) wish.sub(f);
    if (keys['KeyD'] || keys['ArrowRight']) wish.add(r);
    if (keys['KeyA'] || keys['ArrowLeft']) wish.sub(r);
    wish.addScaledVector(f, -moveVec.y);
    wish.addScaledVector(r, moveVec.x);
    if (wish.lengthSq() > 0) wish.normalize().multiplyScalar(sp);

    if (fly) {
      vel.x = wish.x; vel.z = wish.z; vel.y = wish.y;
      if (keys['Space']) vel.y += 22;
      if (keys['ShiftLeft']) vel.y -= 22;
      pos.addScaledVector(vel, dt);
      var fl = W.heightAt(pos.x, pos.z) + 1.4;
      if (pos.y < fl) pos.y = fl;
      grounded = false;
    } else {
      var acc = grounded ? 13 : 5;
      vel.x += (wish.x - vel.x) * Math.min(1, acc * dt);
      vel.z += (wish.z - vel.z) * Math.min(1, acc * dt);
      if (keys['Space']) tryJump();
      vel.y += GRAV * dt;
      pos.x += vel.x * dt; pos.z += vel.z * dt;
      resolve(pos);
      pos.y += vel.y * dt;
      grounded = false;
      resolve(pos);
      var g = W.heightAt(pos.x, pos.z) + PH;
      if (pos.y <= g) { pos.y = g; if (vel.y < 0) vel.y = 0; grounded = true; }
    }

    cam.position.copy(pos);
    cam.rotation.set(0, 0, 0);
    cam.rotateY(yaw); cam.rotateX(pitch);
    if (water) { water.position.x = pos.x; water.position.z = pos.z; }
    skyFollow(pos);
    updateChunks(pos, false);
    pumpChunks(pos.y > 120 ? 3 : 2);
  }

  /* ------------------------------------------------ idle · costs nothing */
  var running = false, idleAt = 0, IDLE_MS = 9000, rafId = 0;
  W.setIdle = function (ms) { IDLE_MS = ms; };
  function wake() {
    idleAt = performance.now();
    if (!running) { running = true; rafId = requestAnimationFrame(loop); hint(false); }
  }
  W.wake = wake;
  function hint(on) {
    var h = document.getElementById('resume');
    if (h) h.classList.toggle('on', !!on);
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') wake();
    else running = false;
  });

  var hbEl, frames = 0, hbT = 0, lastRaf = 0;
  function frame() {
    var dt = Math.min(clock.getDelta(), 0.05);
    hbT += dt;
    if (W.tick) W.tick(W, dt, clock.elapsedTime);
    step(dt);
    renderer.render(scene, cam);
    frames++;
    if (hbT > 1) {
      hbT = 0;
      if (hbEl) hbEl.textContent = frames + ' fps · ' + Math.round(renderer.info.render.triangles / 1000) + 'k';
      frames = 0;
    }
  }
  function loop() {
    if (!running) return;
    lastRaf = performance.now();
    rafId = requestAnimationFrame(loop);
    try { frame(); } catch (e) { running = false; W.diag('frame error: ' + e.message); }
    var moving = keys['KeyW'] || keys['KeyA'] || keys['KeyS'] || keys['KeyD'] || movePid !== null;
    if (moving) idleAt = performance.now();
    if (performance.now() - idleAt > IDLE_MS) { running = false; hint(true); }
  }
  function startLoop() {
    hbEl = document.getElementById('hb');
    running = true;
    idleAt = performance.now();
    rafId = requestAnimationFrame(loop);
    /* if animation frames are starved, a plain timer keeps the world alive */
    setInterval(function () {
      if (running && performance.now() - lastRaf > 400) { try { frame(); } catch (e) {} }
    }, 260);
  }

  addEventListener('resize', function () {
    if (!renderer) return;
    cam.aspect = innerWidth / innerHeight;
    cam.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
    wake();
  });
})();
