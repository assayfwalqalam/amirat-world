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

  /* A shore is not a wall. Land comes DOWN to meet water over a long shelf,
     so every body of water is cut in two stages: a broad shallow valley or
     basin that draws the whole neighbourhood down, and only inside that, the
     channel or the deep. The curve is flat at the rim and steepens toward the
     middle, which is what stops the edge reading as a cliff. */
  function shelf(t) {
    t = Math.min(1, Math.max(0, t));
    return t * t * t * (t * (t * 6 - 15) + 10);
  }
  function riverAt(x, z) {
    var r = ridged(x * 0.00085 + 4.1, z * 0.00085 - 2.7, 3);
    return sstep(0.930, 1.0, r);
  }
  function riverValleyAt(x, z) {
    var r = ridged(x * 0.00085 + 4.1, z * 0.00085 - 2.7, 3);
    return sstep(0.800, 0.985, r);
  }
  function lakeAt(x, z) {
    var l = fbm(x * 0.00062 - 88.3, z * 0.00062 + 12.9, 3);
    return sstep(0.745, 0.815, l);
  }
  function lakeBasinAt(x, z) {
    var l = fbm(x * 0.00062 - 88.3, z * 0.00062 + 12.9, 3);
    return sstep(0.600, 0.790, l);
  }

  /* Places where the water table reaches the surface. A walled desert town is
     built where the water is, never in open sand, so the belt around the walls
     is green and the dunes only begin further out. */
  var OASES = [
    { x: 0, z: 0, r: 300, f: 560 },        /* the town's own palm belt   */
    { x: -430, z: 330, r: 190, f: 420 },   /* the lake and its reed beds */
    { x: 520, z: -240, r: 120, f: 300 }
  ];
  function oasisAt(x, z) {
    var best = 0;
    for (var i = 0; i < OASES.length; i++) {
      var o = OASES[i];
      var d = Math.sqrt((x - o.x) * (x - o.x) + (z - o.z) * (z - o.z));
      var v = 1 - sstep(o.r, o.r + o.f, d);
      if (v > best) best = v;
    }
    return best;
  }
  W.oasisAt = oasisAt;

  W.biomeAt = function (x, z) {
    var moist = fbm(x * 0.00040 + 91.3, z * 0.00040 - 17.7, 3);
    var rocky = fbm(x * 0.00066 - 33.1, z * 0.00066 + 55.9, 3);
    var oa = oasisAt(x, z);
    /* Watered ground, not a lawn: the green comes in clumps with bare sand
       between them, and the edge of the belt is ragged rather than a circle. */
    if (oa > 0.002) {
      var patch = fbm(x * 0.0042 + 5.1, z * 0.0042 - 7.3, 3);
      moist = lerp(moist, 0.79, oa * (0.34 + 0.66 * patch));
    }
    var g = sstep(0.38, 0.58, moist);
    var r = sstep(0.56, 0.73, rocky) * (1 - g * 0.8);
    return { grass: g, rock: r };
  };

  /* ------------------------------------------------ the hand-drawn map
     If the map table sent a world (localStorage amirat_worldmap), its grids
     steer the land: painted mountains rise, painted seas flood, painted
     green grows, painted forests thicken, painted roads run. */
  var MAPW = null;
  try {
    var mraw = localStorage.getItem('amirat_worldmap');
    if (mraw) {
      var mj = JSON.parse(mraw);
      if (mj && mj.n && mj.elev) {
        MAPW = { n: mj.n, world: mj.world || 4096, sites: mj.sites || [] };
        ['elev', 'water', 'green', 'forest', 'palm', 'road'].forEach(function (k) {
          MAPW[k] = new Float32Array(mj[k] || []);
        });
        W.MAPW = MAPW;
      }
    }
  } catch (e) { MAPW = null; }

  function mapAt(grid, x, z) {
    if (!MAPW || !grid || !grid.length) return 0;
    var n = MAPW.n;
    var u = (x / MAPW.world + 0.5) * (n - 1);
    var v = (z / MAPW.world + 0.5) * (n - 1);
    if (u < 0 || v < 0 || u > n - 1 || v > n - 1) return grid === MAPW.elev ? 128 : 0;
    var u0 = Math.floor(u), v0 = Math.floor(v);
    var u1 = Math.min(n - 1, u0 + 1), v1 = Math.min(n - 1, v0 + 1);
    var fu = u - u0, fv = v - v0;
    var a = grid[v0 * n + u0] * (1 - fu) + grid[v0 * n + u1] * fu;
    var b2 = grid[v1 * n + u0] * (1 - fu) + grid[v1 * n + u1] * fu;
    return a * (1 - fv) + b2 * fv;
  }
  /* The painted map is coarse: one cell spans tens of metres, so ANY edge in
     it lands in the world as a wall. Every grid that moves the ground is read
     BLURRED -- nine samples over a wide ring -- so a painted coastline
     arrives as a shelf a hundred metres wide instead of a cliff. */
  function mapSmooth(grid, x, z, r) {
    if (!grid || !grid.length) return 0;
    var sum = mapAt(grid, x, z) * 1.6, wt = 1.6;
    for (var i = 0; i < 8; i++) {
      var a2 = i * 0.7854;
      sum += mapAt(grid, x + Math.cos(a2) * r, z + Math.sin(a2) * r);
      sum += mapAt(grid, x + Math.cos(a2) * r * 0.5, z + Math.sin(a2) * r * 0.5);
      wt += 2;
    }
    return sum / wt;
  }
  W.mapForest = MAPW ? function (x, z) { return mapAt(MAPW.forest, x, z) / 255; } : null;
  W.mapPalm = MAPW ? function (x, z) { return mapAt(MAPW.palm, x, z) / 255; } : null;

  W.heightAt = function (x, z) {
    var b = W.biomeAt(x, z);
    /* the land rides above the water table · only carved basins flood */
    var cont = fbm(x * 0.00055, z * 0.00055, 4);
    var h = (cont - 0.13) * 165;

    /* Dune fields. A sand sea is not corduroy: dunes gather into trains with
       bare sheets of flat sand between them, two sets crossing at an angle,
       and each crest leans downwind so its lee face is short and steep. */
    var sand = (1 - b.grass) * (1 - b.rock * 0.7);
    if (sand > 0.02) {
      var field = fbm(x * 0.00048 + 61.7, z * 0.00048 - 29.4, 3);
      var dmask = sstep(0.40, 0.63, field);
      if (dmask > 0.004) {
        var wx = x + fbm(x * 0.0013 + 21.4, z * 0.0013 - 8.2, 2) * 300;
        var wz = z + fbm(x * 0.0011 - 5.6, z * 0.0011 + 14.9, 2) * 300;
        var ca = 0.8517, sa = 0.5240;          /* first train, +31.6 deg  */
        var cb = 0.4085, sb = -0.9128;         /* second, crossing it     */
        var xa = wx * ca + wz * sa, za = -wx * sa + wz * ca;
        var xb = wx * cb + wz * sb, zb = -wx * sb + wz * cb;
        var r0 = ridged(xa * 0.0038 + 7.7, za * 0.0030 - 3.3, 2);
        var big = ridged((xa + r0 * 130) * 0.0038 + 7.7, za * 0.0030 - 3.3, 3);
        var sml = ridged(xb * 0.0094 - 2.2, zb * 0.0081 + 5.5, 2);
        var d = Math.pow(big * 0.74 + sml * 0.26, 1.75);
        h += (d - 0.19) * 38 * dmask * sand;
      }
    }

    /* ------------------------------------------------------------ relief
       Three systems, none sharing a mask, so the land is not one shape
       repeated at different sizes.

       RIDGES  long chains, ridged noise, tall
       HILLS   rounded swells with convex flanks
       BENCH   flat shelves cut into the slopes, which is what stops a hill
               looking like a heap of sand */
    var mountain = ridged(x * 0.00031 - 55.2, z * 0.00031 + 71.8, 4);
    var mm0 = fbm(x * 0.00019 + 13.7, z * 0.00019 - 41.2, 3);
    var mMask = sstep(0.52, 0.86, mm0);
    /* the foothill skirt: mountains announce themselves long before the wall */
    var skirt = sstep(0.40, 0.88, mm0);
    h += skirt * skirt * 46;
    if (mMask > 0.004) {
      var m2 = ridged(x * 0.00082 + 9.4, z * 0.00082 - 3.1, 3);
      var peak = Math.pow(Math.max(0, mountain - 0.30) / 0.70, 1.55);
      h += peak * 300 * mMask;
      h += Math.pow(Math.max(0, m2 - 0.42), 1.8) * 90 * mMask;
    }

    var swell = fbm(x * 0.00125 - 7.7, z * 0.00125 + 21.3, 4);
    var hMask = sstep(0.34, 0.62, fbm(x * 0.00042 - 61.1, z * 0.00042 + 8.4, 3));
    h += Math.pow(Math.max(0, swell - 0.30) / 0.70, 1.35) * 96 * hMask;

    /* Shelves, but only where there is a mountain to cut them into. Applied
       across open ground this reads as contour lines drawn on a model, which
       is exactly what it looked like the first time. The quantising is also
       softened, so a shelf has a rounded lip rather than a machined step. */
    if (mMask > 0.25) {
      var bench = fbm(x * 0.0007 + 44.4, z * 0.0007 - 12.2, 2);
      var bAmt = sstep(0.52, 0.80, bench) * mMask * sstep(70, 150, h);
      if (bAmt > 0.01) {
        var stepH = 13.0 + 7.0 * fbm(x * 0.0004 - 8.1, z * 0.0004 + 3.3, 2);
        var f2 = h / stepH;
        var fr = f2 - Math.floor(f2);
        /* a soft plateau in the middle of each band, rounded at both lips */
        var soft = Math.floor(f2) + 0.5 + (fr - 0.5) * (1 - sstep(0.12, 0.48, Math.abs(fr - 0.5)));
        h = lerp(h, soft * stepH, bAmt * 0.30);
      }
    }

    var hill = fbm(x * 0.0021 - 12.5, z * 0.0021 + 8.8, 4);
    h += Math.pow(Math.max(0, hill), 1.9) * 165 * b.rock;

    /* the rolling ground: long soft swells everywhere the wall is not,
       the way a meadow or a steppe actually lies */
    h += (fbm(x * 0.0032 + 4.9, z * 0.0032 - 9.1, 3) - 0.5) * 26 * (1 - mMask);
    h += (fbm(x * 0.0065, z * 0.0065, 3) - 0.5) * 15 * (1 - mMask * 0.7);
    h += (fbm(x * 0.021, z * 0.021, 2) - 0.5) * 2.2;

    /* ------------------------------------------------------------- water
       Two stages everywhere: the ground is drawn DOWN over a wide skirt
       first, and only then is the channel or the deep cut inside it. A river
       may run high -- the gate is generous -- but it always brings its
       valley down with it, so no water anywhere ends in a wall. */
    /* Gated on the SLOW height, never on h itself. h carries dunes, hills and
       rolling detail, so a gate reading it flips from off to on within a few
       metres and stands a wall up at the waterline -- which is exactly the
       cliff that was there. The continental form turns over kilometres. */
    var hSlow = (cont - 0.13) * 165 + skirt * skirt * 46;
    var low = sstep(92, 6, hSlow);
    var rval = riverValleyAt(x, z) * low;
    if (rval > 0.001) h -= shelf(rval) * 22.0;          /* the valley */
    var riv = riverAt(x, z) * low;
    if (riv > 0.001) h = lerp(h, WATER_Y - 2.9, shelf(riv));   /* the channel */

    var lbasin = lakeBasinAt(x, z) * sstep(96, 12, hSlow);
    if (lbasin > 0.001) h -= shelf(lbasin) * 26.0;      /* the hollow */
    var lk = lakeAt(x, z) * sstep(70, 10, hSlow);
    if (lk > 0.001) h = lerp(h, WATER_Y - 4.6, shelf(lk));

    /* the lake the town drinks from · carved, not left to the noise. Its rim
       wander used to be half as wide as the blend itself, which locally
       collapsed the shelf to nothing and stood a cliff up out of the water. */
    var ld = Math.sqrt((x + 430) * (x + 430) + (z - 330) * (z - 330));
    var lwob = (fbm(x * 0.0055 - 3.3, z * 0.0055 + 9.1, 2) - 0.5) * 54;
    var lskirt = 1 - sstep(150, 330, ld + lwob);
    if (lskirt > 0) h -= shelf(lskirt) * 16.0;
    var lb = 1 - sstep(84, 240, ld + lwob);
    if (lb > 0) h = lerp(h, WATER_Y - 5.2, shelf(lb));

    /* THE EDGE OF THE WORLD. Past the far ring the land always goes down to
       the sea, over the best part of a kilometre, so the world ends in water
       and never in a wall. The line wanders, so it is a coast and not a
       drawn circle: bays where it comes in, headlands where it runs out. */
    var eD = Math.sqrt(x * x + z * z)
           + (fbm(x * 0.00042 + 71.3, z * 0.00042 - 18.7, 3) - 0.5) * 620
           + (fbm(x * 0.0017 - 3.9, z * 0.0017 + 6.1, 2) - 0.5) * 130;
    if (eD > 2250) {
      h = lerp(h, WATER_Y - 7.0, shelf(sstep(2250, 3250, eD)));
    }

    for (var i = 0; i < FLATS.length; i++) {
      var f = FLATS[i];
      var d = Math.sqrt((x - f.x) * (x - f.x) + (z - f.z) * (z - f.z));
      h = lerp(f.y, h, sstep(f.r, f.r + f.b, d));
    }
    if (MAPW) {
      h += (mapSmooth(MAPW.elev, x, z, 115) - 128) * 0.55;
      /* the painted sea: a wide shelf down to it, not a step off it */
      var mw = mapSmooth(MAPW.water, x, z, 165);
      var wet = sstep(34, 205, mw);
      if (wet > 0.0005) {
        var sink = WATER_Y - 1.2 - sstep(120, 230, mw) * 5.5;
        h = lerp(h, Math.min(h, sink), shelf(wet));
      }
    }
    return h;
  };

  /* how strongly a place has been levelled for building · nothing grows there */
  W.flatAt = function (x, z) {
    var best = 0;
    for (var i = 0; i < FLATS.length; i++) {
      var f = FLATS[i];
      var d = Math.sqrt((x - f.x) * (x - f.x) + (z - f.z) * (z - f.z));
      /* the packed ground reaches the full radius before it starts to give
         way, or grass creeps back in at the corners of a square town */
      var v = 1 - sstep(f.r * 0.96, f.r + f.b * 0.5, d);
      if (v > best) best = v;
    }
    return best;
  };

  /* the trodden road to the gate · nothing grows on a road */
  var ROADS = [];
  W.addRoad = function (x0, z0, x1, z1, halfWidth) {
    ROADS.push({ x0: x0, z0: z0, x1: x1, z1: z1, w: halfWidth || 7 });
  };
  W.roadAt = function (x, z) {
    var best = 0;
    for (var i = 0; i < ROADS.length; i++) {
      var r = ROADS[i];
      var dx = r.x1 - r.x0, dz = r.z1 - r.z0;
      var len2 = dx * dx + dz * dz;
      var t2 = len2 > 0 ? Math.max(0, Math.min(1, ((x - r.x0) * dx + (z - r.z0) * dz) / len2)) : 0;
      var px = r.x0 + dx * t2, pz = r.z0 + dz * t2;
      var d = Math.sqrt((x - px) * (x - px) + (z - pz) * (z - pz));
      var v = 1 - sstep(r.w * 0.55, r.w, d);
      if (v > best) best = v;
    }
    if (MAPW) {
      var mr = mapAt(MAPW.road, x, z) / 255;
      if (mr > best) best = Math.min(1, mr * 1.2);
    }
    return best;
  };

  /* wetness/greenery weights used by the ground shader and the scatterer */
  W.groundWeights = function (x, z, h) {
    var b = W.biomeAt(x, z);
    var wet = sstep(26.0, 0.2, h - WATER_Y);
    var grass = Math.min(1, Math.max(b.grass, wet * 0.92));
    if (MAPW) {
      grass = Math.min(1, Math.max(grass, mapAt(MAPW.green, x, z) / 255));
      wet = Math.min(1, Math.max(wet, mapAt(MAPW.palm, x, z) / 255 * 0.8));
    }
    var rock = Math.min(1, b.rock * 0.9 + sstep(120, 190, h) * 0.7);
    /* ground that has been built on or walked over is packed earth, not meadow */
    var built = Math.max(W.flatAt ? W.flatAt(x, z) : 0, W.roadAt ? W.roadAt(x, z) : 0);
    if (built > 0) {
      grass *= (1 - built);
      wet *= (1 - built * 0.8);
    }
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
    /* Ask the driver what it actually is. An integrated Intel chip in a
       16GB laptop reports plenty of memory and then cannot draw the world,
       so it starts a tier down and the frame watch takes it from there. */
    try {
      var gl0 = renderer.getContext();
      var dbg = gl0.getExtension('WEBGL_debug_renderer_info');
      var gname = dbg ? String(gl0.getParameter(dbg.UNMASKED_RENDERER_WEBGL)) : '';
      W.GPU = gname;
      if (/swiftshader|software|basic render|llvmpipe/i.test(gname)) {
        TIER = 0; W.TIER = 0; W.vegScale = 0.3;
      } else if (/intel|uhd|hd graphics|iris(?!.*xe)|vega \d|radeon r[2-5]|radeon\(tm\) graphics|radeon graphics/i.test(gname)
                 && !/arc|xe max|rx \d|radeon pro/i.test(gname)) {
        /* "AMD Radeon(TM) Graphics" with no model number is the integrated
           graphics in a Ryzen chip. It reports nothing about itself and it
           cannot carry the heaviest world. */
        if (TIER > 1) { TIER = 1; W.TIER = 1; W.vegScale = 0.55; }
      }
    } catch (e) {}
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(TIER === 2 ? Math.min(devicePixelRatio, 1.9) : (TIER === 1 ? Math.min(devicePixelRatio, 1.5) : 1));
    renderer.setClearColor(0x0a0916);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.95;
    renderer.shadowMap.enabled = (TIER === 2);
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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

    initPost();
    initSky();
    initGround();
    initWater();
    initLights();
    if (W.buildAll) W.buildAll(W);
    if (W.EDITOR) primeEditor(); else initPlayer();
    startLoop();
  };

  /* ------------------------------------------------------------- bloom */
  /* every flame, lamp and window blooms into the night, as real light does */
  var composer = null;
  function initPost() {
    if (TIER < 1 || typeof THREE.EffectComposer !== 'function' || typeof THREE.UnrealBloomPass !== 'function') return;
    try {
      composer = new THREE.EffectComposer(renderer);
      composer.addPass(new THREE.RenderPass(scene, cam));
      var bloom = new THREE.UnrealBloomPass(
        new THREE.Vector2(innerWidth, innerHeight),
        TIER === 2 ? 0.30 : 0.22,  /* strength · his rule: light must not flare */
        0.75,                       /* radius */
        0.86                        /* threshold: only true flames glow */
      );
      composer.addPass(bloom);
      W.bloom = bloom;
    } catch (e) { composer = null; W.diag('bloom off: ' + e.message); }
  }

  /* ---------------------------------------------------------------- tex */
  var texWaits = [];
  /* every fetched file carries the build number, or a changed texture keeps
     being served from the player's cache and the new work never lands */
  W.bust = function (url) {
    var v = window.__BUILD;
    if (!v || url.indexOf('?') >= 0 || url.indexOf('data:') === 0) return url;
    return url + '?v=' + v;
  };
  function tex(url, srgb, rep) {
    var t = new THREE.TextureLoader().load(W.bust(url),
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
    W._nightSky = sky;

    moonDir = new THREE.Vector3(0.36, 0.42, -0.83).normalize();
    var mp = moonDir.clone().multiplyScalar(2600);

    halo = new THREE.Mesh(new THREE.PlaneGeometry(1150, 1150),
      new THREE.MeshBasicMaterial({ map: tex('assets/glow.png', true), color: 0xa9b6f0, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, toneMapped: false, opacity: 0.34 }));
    halo.position.copy(mp); scene.add(halo);

    /* Bigger, but tinted just under the bloom threshold · a pure white disc
       blooms into a featureless blob and the face is lost. */
    moonMesh = new THREE.Mesh(new THREE.PlaneGeometry(380, 380),
      new THREE.MeshBasicMaterial({ map: tex('assets/moon.png', true), color: 0xd6dcf0, transparent: true, depthWrite: false, fog: false, toneMapped: false }));
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
    W.starField = [stars(500, 1.7, 0.6), stars(90, 2.7, 0.85)];
    W.starField.forEach(function (s2) { scene.add(s2); });
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
    /* Night light. The sky lights the world faintly and blue; the moon gives
       the only direction. Kept low on purpose, because every fire and lamp in
       the town has to read as the brighter thing -- that is what makes a night
       scene look like night rather than a dim afternoon. */
    var hemi = new THREE.HemisphereLight(0x5b5ea6, 0x241f36, 0.36);
    var amb = new THREE.AmbientLight(0x33325a, 0.16);
    scene.add(hemi); scene.add(amb);
    var moon = new THREE.DirectionalLight(0xc6cdf5, 0.60);
    /* The editor needs to see what it is placing, so it can raise the sun.
       Night is what the game ships with; this only changes the lights. */
    W.setDaylight = function (on) {
      W.DAYLIGHT = !!on;
      hemi.intensity = on ? 1.15 : 0.36;
      hemi.color.setHex(on ? 0xbfd4f2 : 0x5b5ea6);
      hemi.groundColor.setHex(on ? 0x6d5f49 : 0x241f36);
      amb.intensity = on ? 0.42 : 0.16;
      amb.color.setHex(on ? 0x9aa6c4 : 0x33325a);
      moon.intensity = on ? 1.5 : 0.60;
      moon.color.setHex(on ? 0xfff2d8 : 0xc6cdf5);
      renderer.toneMappingExposure = on ? 1.0 : 0.95;
      if (scene.fog) scene.fog.density = on ? 0.00035 : 0.00105;
      if (W.groundNight) W.groundNight.value = on ? 0.0 : 1.0;
      if (W.bloom) W.bloom.strength = on ? 0.12 : (TIER === 2 ? 0.40 : 0.28);
      /* the sky is a night photograph, so daylight needs its own backdrop */
      if (on) {
        if (!W._daySky) W._daySky = new THREE.Color(0x9fc0e8);
        scene.background = W._daySky;
      } else if (W._nightSky) {
        scene.background = W._nightSky;
      }
      if (moonMesh) moonMesh.visible = !on;
      if (halo) halo.visible = !on;
      clouds.forEach(function (c) { c.m.visible = !on; });
      if (W.starField) W.starField.forEach(function (s2) { s2.visible = !on; });
    };
    moon.position.copy(moonDir).multiplyScalar(900);
    if (TIER === 2) {
      moon.castShadow = true;
      /* A 460-metre shadow box over 2048 texels is a quarter of a metre per
         texel, which cannot hold the edge of a step; and a normal bias of 0.6
         pushes the shadow most of a metre off whatever casts it, so nothing
         looked attached to the ground. Tighter box, bigger map, small bias. */
      moon.shadow.mapSize.set(4096, 4096);
      var c = moon.shadow.camera;
      c.near = 500; c.far = 1400;
      c.left = -125; c.right = 125; c.top = 125; c.bottom = -125;
      moon.shadow.bias = -0.00035;
      moon.shadow.normalBias = 0.045;
      W.moonLight = moon;
      W.moonTarget = new THREE.Object3D();
      scene.add(W.moonTarget);
      moon.target = W.moonTarget;
    }
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
      sh.uniforms.uNight = { value: 1.0 };
      W.groundNight = sh.uniforms.uNight;

      sh.vertexShader = 'varying vec3 vWPos;\nvarying vec3 vWNrm;\n' + sh.vertexShader.replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\n vWPos = (modelMatrix * vec4(transformed,1.0)).xyz;\n vWNrm = normalize(mat3(modelMatrix) * objectNormal);'
      );

      sh.fragmentShader = 'uniform sampler2D tSand;\nuniform sampler2D tGrav;\nuniform sampler2D tRock;\nuniform sampler2D tGrass;\nuniform sampler2D tMask;\nuniform float uNight;\nvarying vec3 vWPos;\nvarying vec3 vWNrm;\n' + sh.fragmentShader;
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
          'vec3 sA2 = texture2D(tSand, wxz * -0.067 + vec2(0.41, 0.77)).rgb;',
          'sA = mix(sA, sA2, smoothstep(0.36, 0.62, macro2));',
          'vec3 sB = texture2D(tGrav, wxz * 0.052).rgb;',
          'vec3 sC = texture2D(tSand, wxz * 0.0143).rgb;',
          'vec3 sand = mix(sA, sB, smoothstep(0.40, 0.66, macro));',
          'sand *= (0.62 + 0.82 * sC.r) * (0.80 + 0.42 * macro2);',
          /* ---- the rock, and the cliffs it makes.
             Ground texture is projected straight down, which is fine for a
             field and ruinous for a wall: a vertical face has no footprint to
             sample, so one row of pixels stretches down its whole height. It
             is projected from three sides instead, and on a flat field the
             upward projection still wins, so nothing else changes.
             What a real cliff shows, from the photographs: beds of different
             coloured stone, rain fluting combed vertically down the face, a
             hard cap on each bed that catches the light while its soft
             underside stays in shadow. */
          'float slope = 1.0 - clamp(vWNrm.y, 0.0, 1.0);',
          'float cliff = smoothstep(0.40, 0.76, slope);',
          'vec3 bw = pow(abs(vWNrm), vec3(4.0));',
          'bw /= max(1e-4, bw.x + bw.y + bw.z);',
          'vec3 rock = (texture2D(tRock, vWPos.zy * 0.058).rgb * bw.x',
          '          +  texture2D(tRock, wxz      * 0.058).rgb * bw.y',
          '          +  texture2D(tRock, vWPos.xy * 0.058).rgb * bw.z);',
          'vec3 rB = texture2D(tRock, wxz * 0.0121 + vec2(0.5)).rgb;',
          'float rGrain = dot(rock, vec3(0.34, 0.5, 0.16));',
          'rock *= (0.66 + 0.78 * rB.r);',
          'if (cliff > 0.004) {',
          /* the beds, warped so they are not ruled lines, each its own stone */
          /* Two systems, not one. Thick FORMATIONS of a single stone, each
             many metres deep and each its own colour, and inside every one
             its own LAMINATIONS at its own thickness. One evenly spaced
             stripe repeated up the whole wall is corrugated card, not rock,
             and red beds are rare: most stone here is cream and grey. */
          '  float warpY = 3.4 * texture2D(tMask, wxz * 0.0021 + vec2(0.31, 0.62)).r;',
          '  float fy = (vWPos.y + warpY * 2.2) * 0.052;',
          '  float fi = floor(fy);',
          '  float fh = fract(sin(fi * 12.9898) * 43758.545);',
          '  float fh2 = fract(sin(fi * 45.164) * 31718.927);',
          '  float bedH = mix(0.55, 3.4, fh2);',
          '  float by = (vWPos.y + warpY) / bedH;',
          '  float bhh = fract(sin(floor(by) * 78.233 + fi * 3.7) * 24634.633);',
          '  vec3 bed = mix(vec3(0.86, 0.82, 0.73), vec3(0.66, 0.64, 0.61), smoothstep(0.26, 0.60, fh));',
          '  bed = mix(bed, vec3(0.80, 0.67, 0.50), smoothstep(0.56, 0.80, fh));',
          '  bed = mix(bed, vec3(0.70, 0.42, 0.29), smoothstep(0.89, 0.975, fh));',
          '  bed *= 0.90 + 0.20 * bhh;',
          /* the cap of a bed stands proud, the soft rock beneath it is undercut */
          '  float f = fract(by);',
          '  float lip = smoothstep(0.85, 1.0, f) * 0.24 - smoothstep(0.17, 0.0, f) * 0.17;',
          /* rain fluting: channels running down the face, spaced along its own
             horizontal direction so they stay vertical whichever way it turns */
          '  vec2 tang = normalize(vec2(-vWNrm.z, vWNrm.x) + vec2(1e-5));',
          '  float u = dot(wxz, tang);',
          '  float rib = sin(u * 2.7 + fh2 * 6.28) * 0.50',
          '            + sin(u * 6.9 + fh * 4.10) * 0.30',
          '            + sin(u * 16.3) * 0.20;',
          '  vec3 cliffC = bed * (0.70 + 0.50 * (rib * 0.5 + 0.5)) * (1.0 + lip);',
          /* the photographed grain, held down: a ground photo dragged up a
             wall shows its own weave, and at full strength it reads as cloth */
          '  cliffC *= 0.82 + 0.36 * rGrain;',
          '  rock = mix(rock, cliffC, cliff);',
          '}',
          /* grass */
          'vec3 gA = texture2D(tGrass, wxz * 0.098).rgb;',
          'vec3 gA2 = texture2D(tGrass, wxz * -0.074 + vec2(0.53, 0.21)).rgb;',
          'gA = mix(gA, gA2, smoothstep(0.34, 0.66, macro2));',
          'vec3 gA3 = texture2D(tGrass, wxz * 0.041 + vec2(0.83, 0.47)).rgb;',
          'gA = mix(gA, gA3, smoothstep(0.30, 0.62, fine));',
          'vec3 gB = texture2D(tGrass, wxz * 0.0172 + vec2(0.2, 0.7)).rgb;',
          /* the green meadow: tone drifts in big soft patches, never in tiles */
          'vec3 grass = gA * (0.62 + 0.80 * gB.g);',
          'grass *= vec3(0.90, 1.0, 0.78) * (0.74 + 0.52 * macro2);',
          /* the dry grassland: the same sheet pulled to straw gold */
          'vec3 dry = mix(vec3(dot(gA, vec3(0.33, 0.5, 0.17))), gA, 0.30);',
          'dry *= vec3(1.30, 1.06, 0.60) * (0.80 + 0.45 * macro);',
          /* a face this steep is stone whatever grows on the flat beside it */
          'float wRock = clamp(vColor.g + smoothstep(0.30, 0.62, slope) - 0.10 * vColor.r + cliff * 0.85, 0.0, 1.0);',
          /* one ramp for all land: bare sand only where nothing grows at all */
          'float gW = clamp(vColor.r * (0.85 + 0.3 * fine), 0.0, 1.0);',
          'vec3 col = mix(sand, dry, smoothstep(0.06, 0.38, gW));',
          'col = mix(col, grass, smoothstep(0.44, 0.76, gW));',
          'col = mix(col, rock, wRock);',
          /* Rubble does not cling to a wall. It falls off it and piles at the
             foot, so the loose stuff belongs on the gentler slopes below the
             cliff, and the cliff itself stays bare rock. */
          'float apron = smoothstep(0.07, 0.19, slope) * (1.0 - smoothstep(0.30, 0.54, slope));',
          'vec3 scree = texture2D(tGrav, wxz * 0.19).rgb * (0.7 + 0.7 * texture2D(tRock, wxz * 0.031).r);',
          'col = mix(col, scree * 0.92, apron * 0.66 * clamp(vColor.g + cliff, 0.0, 1.0));',
          'float hollow = 1.0 - smoothstep(0.02, 0.16, slope);',
          'vec3 grit2 = texture2D(tGrav, wxz * 0.33 + vec2(0.4, 0.9)).rgb;',
          'col = mix(col, col * (0.72 + 0.66 * grit2.r), hollow * 0.34 * (1.0 - vColor.r));',
          'col = mix(col, col * vec3(0.70, 0.76, 0.70), vColor.b * 0.55);',
          /* Inside the walls the ground is trodden: compacted grey-tan earth
             with pebbles pressed in, not loose desert. */
          'float townD = length(wxz);',
          'float town = 1.0 - smoothstep(128.0, 182.0, townD);',
          'vec3 trodA = texture2D(tGrav, wxz * 0.115).rgb;',
          'vec3 trodB = texture2D(tSand, wxz * 0.034 + vec2(0.6, 0.2)).rgb;',
          'vec3 trod = mix(trodA, trodB, 0.42);',
          'trod = mix(trod, vec3(dot(trod, vec3(0.36, 0.5, 0.14))), 0.55) * vec3(1.05, 0.99, 0.90);',
          'trod *= (0.78 + 0.38 * macro2) * (0.90 + 0.20 * fine);',
          'col = mix(col, trod, town * 0.85);',
          'col *= 0.94 + 0.12 * fine;',
          /* Grain underfoot. The broad layers repeat every ten metres or so,
             which is smooth mush at arm's length, so a fine layer fades in
             close to the eye and is gone before it can shimmer at distance. */
          'float camD = length(vWPos - cameraPosition);',
          'float nearW = 1.0 - smoothstep(3.0, 30.0, camD);',
          'if (nearW > 0.002) {',
          '  vec3 grain = texture2D(tSand, wxz * 0.62).rgb;',
          '  vec3 fine2 = texture2D(tGrav, wxz * 3.1).rgb;',
          '  vec3 grit  = texture2D(tGrav, wxz * 1.35).rgb;',
          '  float g = grain.r * 0.48 + grit.r * 0.30 + fine2.r * 0.22;',
          '  col *= mix(1.0, 0.80 + 0.40 * g, nearW * 0.38);',
          '}',
          /* Moonlight is blue, and photographed daylight sand is far too bright
             to stand in for ground at night: left alone it reads as lit
             concrete and outshines the walls it should sit beneath. */
          'col = mix(col, vec3(dot(col, vec3(0.34, 0.5, 0.16))) * vec3(0.78, 0.85, 1.08), 0.34 * uNight);',
          'col *= mix(1.0, 0.52, uNight);',
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
      try {
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
      } catch (e) {
        /* one chunk may fail; the world may not go bald for it */
        W.diag && W.diag('veg: ' + e.message);
      }
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
    vegVisible(p);
  }

  /* On a machine that cannot keep up, the vegetation is drawn nearer rather
     than thinned: a half-empty meadow looks broken, a meadow that ends in the
     dark does not. Driven by the quality watch, not by a guess about the
     hardware. */
  function vegVisible(p) {
    var R = W.vegDrawR || 1e9;
    if (R > 1e8) {
      chunks.forEach(function (rec) {
        if (rec.veg) for (var i = 0; i < rec.veg.length; i++) rec.veg[i].visible = true;
      });
      return;
    }
    var R2 = R * R;
    chunks.forEach(function (rec) {
      if (!rec.veg) return;
      var cx = rec.ci * CH + CH / 2 - p.x, cz = rec.cj * CH + CH / 2 - p.z;
      var on = (cx * cx + cz * cz) < R2;
      for (var i = 0; i < rec.veg.length; i++) rec.veg[i].visible = on;
    });
  }
  W.vegVisible = vegVisible;

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
  var waterMat = null, waterFlow = null;
  function initWater() {
    var wn = tex('assets/water_n.jpg', false, true);
    var g = new THREE.PlaneGeometry(7000, 7000, 1, 1);
    g.rotateX(-Math.PI / 2);
    var m = new THREE.MeshStandardMaterial({
      color: 0x16203c, roughness: 0.14, metalness: 0.55,
      normalMap: wn, normalScale: new THREE.Vector2(0.55, 0.55),
      transparent: true, opacity: 0.93
    });
    m.onBeforeCompile = function (sh) {
      sh.uniforms.uFlow = { value: 0 };
      waterFlow = sh.uniforms.uFlow;
      sh.vertexShader = 'varying vec3 vWaterPos;\n' + sh.vertexShader.replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\n vWaterPos = (modelMatrix * vec4(transformed,1.0)).xyz;'
      );
      sh.fragmentShader = 'uniform float uFlow;\nvarying vec3 vWaterPos;\n' + sh.fragmentShader;
      /* Two sheets of ripple, taken from world position so they stay where
         they are however far you walk, drifting at different speeds so the
         pattern never sits still and never repeats visibly. */
      sh.fragmentShader = sh.fragmentShader.replace(
        '#include <normal_fragment_maps>',
        [
          'vec2 wUv = vWaterPos.xz * 0.045;',
          'vec3 nA = texture2D( normalMap, wUv + vec2( uFlow * 0.021, uFlow * 0.013) ).xyz * 2.0 - 1.0;',
          'vec3 nB = texture2D( normalMap, wUv * 0.47 + vec2(-uFlow * 0.011, uFlow * 0.024) ).xyz * 2.0 - 1.0;',
          'vec3 nC = texture2D( normalMap, wUv * 2.3 + vec2( uFlow * 0.04, -uFlow * 0.031) ).xyz * 2.0 - 1.0;',
          'vec3 mapN = normalize(nA + nB * 0.8 + nC * 0.35);',
          'mapN.xy *= normalScale;',
          /* build the frame ourselves: some compile paths have no tbn */
          'vec3 wq0 = dFdx(-vViewPosition); vec3 wq1 = dFdy(-vViewPosition);',
          'vec2 wst0 = dFdx(wUv); vec2 wst1 = dFdy(wUv);',
          'vec3 wN = normalize(normal);',
          'vec3 wT = normalize(wq0 * wst1.t - wq1 * wst0.t);',
          'vec3 wB = -normalize(cross(wN, wT));',
          'normal = normalize(mat3(wT, wB, wN) * mapN);'
        ].join('\n'));
    };
    water = new THREE.Mesh(g, m);
    water.position.y = WATER_Y;
    water.renderOrder = 1;
    waterMat = m;
    scene.add(water);
    W.water = water;
  }
  W.tickWater = function (t) { if (waterFlow) waterFlow.value = t; };

  /* ------------------------------------------------------------ physics */
  var COLL = [];          /* oriented boxes */
  var GRID = new Map();   /* spatial hash */
  var CELL = 26;
  function cellKey(x, z) { return Math.floor(x / CELL) + ',' + Math.floor(z / CELL); }

  var boxId = 0;
  W.addBox = function (cx, cy, cz, hx, hy, hz, rot) {
    var b = { id: ++boxId,
              cx: cx, cz: cz, hx: hx, hz: hz, y0: cy - hy, y1: cy + hy, rot: rot || 0,
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
          if (b.dead || seen[b.id]) continue;
          seen[b.id] = 1;
          out.push(b);
        }
      }
    }
    return out;
  };

  /* ------------------------------------------------------------- player */
  var PR = 0.42, PH = 1.72, STEP = 0.74, GRAV = -23.5, JUMP = 8.4;
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
    var at = q.get('at');            /* ?at=x,z,h · stand anywhere, for inspection */
    if (at) {
      var pa = at.split(',').map(Number);
      pos.set(pa[0] || 0, W.heightAt(pa[0] || 0, pa[1] || 0) + (pa[2] || PH), pa[1] || 0);
      if (q.get('yaw')) yaw = Number(q.get('yaw'));
      if (q.get('fly')) fly = true;
      var so2 = document.getElementById('start');
      if (so2) so2.classList.add('off');
      W.SHOT_MODE = true;
      W.setIdle(1e9);
    }
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
      W.SHOT_MODE = true;
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
      /* rotation.y carries local +x to world (cos, -sin); this is its inverse */
      var lx = dx * b.c - dz * b.s;
      var lz = dx * b.s + dz * b.c;
      var ox = b.hx + PR - Math.abs(lx);
      var oz = b.hz + PR - Math.abs(lz);
      if (ox <= 0 || oz <= 0) continue;
      /* stand on top when the ledge is a step's height away */
      if (b.y1 - feet <= STEP && b.y1 - feet > -0.05 && vel.y <= 0.01) {
        p.y = b.y1 + PH; vel.y = 0; grounded = true; continue;
      }
      if (ox < oz) { lx += (lx > 0 ? ox : -ox); } else { lz += (lz > 0 ? oz : -oz); }
      p.x = b.cx + lx * b.c + lz * b.s;
      p.z = b.cz - lx * b.s + lz * b.c;
    }
  }

  /* The editor flies its own camera and wants no gravity, no collision and no
     idle pause. It drives pos/yaw/pitch through W.camState and everything
     downstream -- streaming, sky, water, the moon -- carries on unchanged. */
  /* The editor brings its own controls, so none of the player's pointer-lock,
     touch or joystick handling is wanted -- only a start position and a primed
     set of terrain chunks. */
  function primeEditor() {
    pos.set(0, W.heightAt(0, 140) + 34, 210);
    yaw = Math.PI; pitch = -0.42;
    W.setIdle(1e9);
    updateChunks(pos, true);
    pumpChunks(80);
  }

  W.camState = function (o) {
    if (o) {
      if (o.x !== undefined) pos.set(o.x, o.y, o.z);
      if (o.yaw !== undefined) yaw = o.yaw;
      if (o.pitch !== undefined) pitch = o.pitch;
    }
    return { x: pos.x, y: pos.y, z: pos.z, yaw: yaw, pitch: pitch };
  };
  W.keyHeld = function (code) { return !!keys[code]; };

  function step(dt) {
    if (W.EDITOR) {
      if (W.editorStep) W.editorStep(dt);
      cam.position.copy(pos);
      cam.rotation.set(0, 0, 0);
      cam.rotateY(yaw); cam.rotateX(pitch);
      if (water) { water.position.x = pos.x; water.position.z = pos.z; }
      if (W.moonLight) {
        W.moonTarget.position.set(pos.x, pos.y - 2, pos.z);
        W.moonTarget.updateMatrixWorld();
        W.moonLight.position.copy(moonDir).multiplyScalar(900).add(
          new THREE.Vector3(pos.x, 0, pos.z));
      }
      skyFollow(pos);
      updateChunks(pos, false);
      pumpChunks(pos.y > 120 ? 4 : 3);
      return;
    }
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
    if (W.moonLight) {
      W.moonTarget.position.set(pos.x, pos.y - 2, pos.z);
      W.moonTarget.updateMatrixWorld();
      W.moonLight.position.copy(moonDir).multiplyScalar(900).add(
        new THREE.Vector3(pos.x, 0, pos.z));
    }
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

  /* ------------------------------------------------- keeping up, measured
     navigator.deviceMemory reports RAM, not the graphics chip, so a laptop
     with plenty of memory and a weak integrated GPU was handed the heaviest
     world and crawled. Guessing from what the browser admits to is not good
     enough: the frame time itself decides. If the machine cannot hold the
     target, quality steps down until it can, and it says so on screen.

     Cheap first, drastic last: resolution, then the glow, then the shadows,
     then how far the vegetation is drawn. */
  var QSTEP = 0, QMAX = 4, qBudget = 0, qHold = 0, rafDriven = false;
  function applyQuality() {
    var pr = [1.9, 1.5, 1.25, 1.0, 0.75][QSTEP];
    renderer.setPixelRatio(Math.min(devicePixelRatio, pr));
    if (W.bloom) W.bloom.enabled = QSTEP < 2;
    if (W.moonLight) W.moonLight.castShadow = (QSTEP < 3) && TIER === 2;
    /* the far vegetation is the last thing to go, and the first thing a weak
       machine cannot afford */
    W.vegDrawR = [1e9, 1e9, 260, 190, 130][QSTEP];
    try { vegVisible(W.getPos()); } catch (e) {}
    if (hbEl) hbEl.title = 'quality step ' + QSTEP;
  }
  W.applyQuality = applyQuality;
  function qualityWatch(dt) {
    /* Judge only frames that ANIMATION drove. When the tab is hidden or
       animation frames are starved, the fallback timer paces the world at
       a quarter second, and reading that as a slow frame would strip the
       world to nothing while nobody is even looking at it. */
    if (!rafDriven || document.visibilityState !== 'visible') return;
    if (clock.elapsedTime < 1.5) return;
    var ms = dt * 1000;
    qBudget = qBudget * 0.88 + ms * 0.12;
    if (qHold > 0) { qHold -= dt; return; }
    if (qBudget > 34 && QSTEP < QMAX) {          /* under 30 fps */
      QSTEP += (qBudget > 60 ? 2 : 1);
      if (QSTEP > QMAX) QSTEP = QMAX;
      applyQuality();
      qHold = 3.0;                                /* let it settle before judging again */
      W.diag('eased quality to step ' + QSTEP + ' (' + Math.round(qBudget) + 'ms frames)');
    } else if (qBudget < 15 && QSTEP > 0 && clock.elapsedTime > 12) {
      QSTEP -= 1;                                 /* it has room again */
      applyQuality();
      qHold = 6.0;
    }
  }

  var hbEl, frames = 0, hbT = 0, lastRaf = 0;
  function frame() {
    var dt = Math.min(clock.getDelta(), 0.05);
    hbT += dt;
    if (W.tickWater) W.tickWater(clock.elapsedTime);
    if (W.tick) W.tick(W, dt, clock.elapsedTime);
    step(dt);
    if (composer) composer.render(); else renderer.render(scene, cam);
    qualityWatch(dt);
    frames++;
    if (hbT > 1) {
      hbT = 0;
      if (hbEl) hbEl.textContent = frames + ' fps · ' +
        Math.round(renderer.info.render.triangles / 1000) + 'k · q' + QSTEP;
      frames = 0;
    }
  }
  function loop() {
    if (!running) return;
    rafDriven = true;
    lastRaf = performance.now();
    rafId = requestAnimationFrame(loop);

    /* A fixed viewpoint keeps asking for frames but stops drawing once the
       world has settled. Headless capture advances a virtual clock through
       animation frames, so the loop must keep spinning or the clock stalls
       and the screenshot never fires; it just must stop costing anything.
       The canvas holds the last drawn frame, which is the one we want. */
    if (W.SHOT_MODE && shotDone) return;

    try { frame(); } catch (e) { running = false; W.diag('frame error: ' + e.message); }

    if (W.SHOT_MODE) {
      if (W.MODELS_IN && pending.length === 0) shotFrames++; else shotFrames = 0;
      if (shotFrames > 30) { shotDone = true; document.title = 'settled'; }
      return;
    }
    var moving = keys['KeyW'] || keys['KeyA'] || keys['KeyS'] || keys['KeyD'] || movePid !== null;
    if (moving) idleAt = performance.now();
    if (performance.now() - idleAt > IDLE_MS) { running = false; hint(true); }
  }
  var shotFrames = 0, shotDone = false;
  function startLoop() {
    hbEl = document.getElementById('hb');
    running = true;
    idleAt = performance.now();
    rafId = requestAnimationFrame(loop);
    /* if animation frames are starved, a plain timer keeps the world alive */
    setInterval(function () {
      if (running && performance.now() - lastRaf > 400) {
        rafDriven = false;
        try { frame(); } catch (e) {}
      }
    }, 260);
  }

  addEventListener('resize', function () {
    if (!renderer) return;
    cam.aspect = innerWidth / innerHeight;
    cam.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
    if (composer) composer.setSize(innerWidth, innerHeight);
    wake();
  });
})();
