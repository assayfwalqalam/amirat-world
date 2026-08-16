/* Amiratu al-Ulum · the built world
   Town walls and gates, mosque, palace, library, houses, camps, caves,
   fire and lamplight, and everything that grows. */
(function () {
  'use strict';
  var W = window.W;
  var T = THREE;

  var MODELS = {};
  var doors = [];
  var fires = [];
  var lamps = [];
  var winds = [];
  var loader = null;

  /* every flame and lamp registers here; a small pool of real lights
     follows whichever are nearest, so the shaders stay cheap everywhere */
  var EMIT = [];
  var POOL = [];
  var POOL_N = 6;
  function initPool() {
    for (var i = 0; i < POOL_N; i++) {
      var l = new T.PointLight(0xffa445, 0, 26, 1.9);
      l.position.set(0, -9999, 0);
      W.scene.add(l);
      POOL.push(l);
    }
  }
  function driveLights(t) {
    var cp = W.cam.position;
    for (var i = 0; i < EMIT.length; i++) {
      var e = EMIT[i];
      var dx = e.x - cp.x, dy = e.y - cp.y, dz = e.z - cp.z;
      e.d2 = dx * dx + dy * dy + dz * dz;
    }
    /* partial selection of the nearest few */
    var best = [];
    for (var k = 0; k < EMIT.length; k++) {
      var e2 = EMIT[k];
      if (e2.d2 > 6400) continue;
      if (best.length < POOL_N) { best.push(e2); best.sort(function (a, b) { return a.d2 - b.d2; }); }
      else if (e2.d2 < best[POOL_N - 1].d2) { best[POOL_N - 1] = e2; best.sort(function (a, b) { return a.d2 - b.d2; }); }
    }
    for (var p = 0; p < POOL_N; p++) {
      var L = POOL[p], src = best[p];
      if (!src) { L.intensity = 0; continue; }
      var fl = src.steady
        ? 0.92 + 0.08 * Math.sin(t * 3.1 + src.ph)
        : 0.72 + 0.28 * (0.5 + 0.5 * (Math.sin(t * 11 + src.ph) * 0.5 + Math.sin(t * 23.3 + src.ph * 2) * 0.3 + Math.sin(t * 4.1 + src.ph) * 0.2));
      L.color.setHex(src.col);
      L.distance = src.reach;
      L.position.set(src.x, src.y, src.z);
      L.intensity = src.base * fl;
      src.lit = fl;
    }
  }

  /* ------------------------------------------------------------ helpers */
  function mat(map, color, rough, rep) {
    var m = new T.MeshStandardMaterial({ color: color || 0xffffff, roughness: rough === undefined ? 0.95 : rough, metalness: 0 });
    if (map) {
      var t = W.tex(map, true, true);
      if (rep) t.repeat.set(rep[0], rep[1]);
      m.map = t;
    }
    return m;
  }

  var M = {};
  function initMats() {
    M.brick = mat('assets/mudbrick.jpg', 0xd6b184, 1, [1, 1]);
    M.brick2 = mat('assets/mudbrick.jpg', 0xc09a72, 1, [1, 1]);
    M.stone = mat('assets/sandstone.jpg', 0xe4c79a, 1, [1, 1]);
    M.stone2 = mat('assets/sandstone.jpg', 0xcdb086, 1, [1, 1]);
    M.cloth = mat('assets/cloth.jpg', 0xbba98e, 1, [1, 1]);
    M.wood = new T.MeshStandardMaterial({ color: 0x5a3d24, roughness: 0.9 });
    M.dark = new T.MeshStandardMaterial({ color: 0x241a12, roughness: 1 });
    M.metal = new T.MeshStandardMaterial({ color: 0x2a2118, roughness: 0.45, metalness: 0.7 });
    M.gold = new T.MeshStandardMaterial({ color: 0xb8913f, roughness: 0.36, metalness: 0.85 });
    M.win = new T.MeshBasicMaterial({ color: 0xffab52, toneMapped: false });
    M.winOff = new T.MeshBasicMaterial({ color: 0x0a0b16 });
    M.floor = new T.MeshStandardMaterial({ color: 0x7d6647, roughness: 1 });
  }

  /* a solid box: drawn and collided */
  function box(w, h, d, x, y, z, m, rot, solid) {
    var g = new T.Mesh(new T.BoxGeometry(w, h, d), m || M.brick);
    g.position.set(x, y, z);
    if (rot) g.rotation.y = rot;
    W.scene.add(g);
    if (solid !== false) W.addBox(x, y, z, w / 2, h / 2, d / 2, rot || 0);
    return g;
  }
  function cyl(rt, rb, h, seg, x, y, z, m, solid) {
    var g = new T.Mesh(new T.CylinderGeometry(rt, rb, h, seg), m || M.stone);
    g.position.set(x, y, z);
    W.scene.add(g);
    if (solid !== false) W.addBox(x, y, z, Math.max(rt, rb) * 0.86, h / 2, Math.max(rt, rb) * 0.86, 0);
    return g;
  }
  function dome(r, x, y, z, m, seg) {
    var g = new T.Mesh(new T.SphereGeometry(r, seg || 26, Math.max(10, (seg || 26) / 2), 0, Math.PI * 2, 0, Math.PI * 0.52), m || M.stone);
    g.position.set(x, y, z);
    W.scene.add(g);
    return g;
  }
  function finial(x, y, z, s) {
    var g = new T.Mesh(new T.ConeGeometry(0.22 * s, 1.5 * s, 8), M.gold);
    g.position.set(x, y + 0.75 * s, z);
    W.scene.add(g);
    var b = new T.Mesh(new T.SphereGeometry(0.34 * s, 10, 8), M.gold);
    b.position.set(x, y + 0.1 * s, z);
    W.scene.add(b);
  }
  /* an arched opening drawn as a header over a gap */
  function arch(w, h, d, x, y, z, m, rot) {
    var steps = 9;
    for (var i = 0; i < steps; i++) {
      var a = Math.PI * (i + 0.5) / steps;
      var bx = -Math.cos(a) * w / 2, by = Math.sin(a) * (h * 0.5);
      var bw = (Math.PI * w / 2) / steps * 1.25;
      var seg = new T.Mesh(new T.BoxGeometry(bw, 0.55, d), m || M.stone);
      var c = Math.cos(rot || 0), s = Math.sin(rot || 0);
      seg.position.set(x + bx * c, y + by, z + bx * s);
      seg.rotation.y = rot || 0;
      seg.rotation.z = a - Math.PI / 2;
      W.scene.add(seg);
    }
  }

  /* --------------------------------------------------------------- fire */
  var flameTex = [];
  function initFire() {
    for (var i = 0; i < 3; i++) {
      var t = W.tex('assets/flame.png', true);
      t.repeat.set(1, 1 / 8);
      flameTex.push(t);
    }
  }
  /* a living flame: animated sheet, flickering light, tight glow, no blob */
  function fire(x, y, z, scale, power) {
    scale = scale || 1; power = power === undefined ? 1 : power;
    var tx = flameTex[fires.length % 3];
    var m = new T.Mesh(new T.PlaneGeometry(0.5 * scale, 0.78 * scale),
      new T.MeshBasicMaterial({ map: tx, transparent: true, blending: T.AdditiveBlending, depthWrite: false, toneMapped: false, opacity: 0.96 }));
    m.position.set(x, y + 0.36 * scale, z);
    W.scene.add(m);

    var core = new T.Mesh(new T.PlaneGeometry(1.5 * scale, 1.5 * scale),
      new T.MeshBasicMaterial({ map: W.tex('assets/glow.png', true), color: 0xffc070, transparent: true, blending: T.AdditiveBlending, depthWrite: false, toneMapped: false, opacity: 0.5 }));
    core.position.set(x, y + 0.3 * scale, z);
    W.scene.add(core);

    var f = { m: m, core: core, base: 2.3 * power, reach: 26 * Math.sqrt(power),
              x: x, y: y + 0.55 * scale, z: z, col: 0xffa445,
              ph: Math.random() * 10, sc: scale, frame: 0, lit: 1 };
    fires.push(f);
    EMIT.push(f);
    return f;
  }
  /* a hanging lamp: warm pool of light that fades at its reach */
  function lamp(x, y, z, power, model) {
    var g = new T.Mesh(new T.PlaneGeometry(1.05, 1.05),
      new T.MeshBasicMaterial({ map: W.tex('assets/glow.png', true), color: 0xffd08a, transparent: true, blending: T.AdditiveBlending, depthWrite: false, toneMapped: false, opacity: 0.62 }));
    g.position.set(x, y, z);
    W.scene.add(g);
    var e = { g: g, base: power || 1.5, reach: 22, x: x, y: y, z: z, col: 0xffb367,
              ph: Math.random() * 9, steady: 1, lit: 1 };
    lamps.push(e);
    EMIT.push(e);
    if (model !== false) place('lantern', x, y - 0.34, z, 0.62, Math.random() * 3);
    return e;
  }
  /* a torch on a wall: bracket, flame, and a shaft of light down the stone */
  function torch(x, y, z, rot) {
    var post = new T.Mesh(new T.CylinderGeometry(0.055, 0.07, 0.86, 6), M.wood);
    post.position.set(x, y, z);
    post.rotation.z = 0.36 * Math.cos(rot || 0);
    post.rotation.x = -0.36 * Math.sin(rot || 0);
    W.scene.add(post);
    var cup = new T.Mesh(new T.CylinderGeometry(0.13, 0.08, 0.2, 8), M.metal);
    cup.position.set(x, y + 0.44, z);
    W.scene.add(cup);
    fire(x, y + 0.5, z, 0.95, 1.15);
    var ray = new T.Mesh(new T.PlaneGeometry(2.5, 3.4),
      new T.MeshBasicMaterial({ map: W.tex('assets/ray.png', true), color: 0xffbe72, transparent: true, blending: T.AdditiveBlending, depthWrite: false, toneMapped: false, opacity: 0.2 }));
    ray.position.set(x, y - 1.0, z);
    ray.rotation.y = rot || 0;
    W.scene.add(ray);
  }

  /* -------------------------------------------------------------- doors */
  function door(x, y, z, w, h, rot, m) {
    var pivot = new T.Group();
    pivot.position.set(x, y, z);
    pivot.rotation.y = rot;
    var leaf = new T.Mesh(new T.BoxGeometry(w, h, 0.14), m || M.wood);
    leaf.position.set(w / 2, h / 2, 0);
    pivot.add(leaf);
    var knob = new T.Mesh(new T.SphereGeometry(0.06, 8, 6), M.gold);
    knob.position.set(w - 0.18, h * 0.5, 0.1);
    pivot.add(knob);
    W.scene.add(pivot);
    var cx = x + Math.cos(rot) * w / 2, cz = z + Math.sin(rot) * w / 2;
    var col = W.addBox(cx, y + h / 2, cz, w / 2, h / 2, 0.1, rot);
    var d = { pivot: pivot, col: col, open: false, ang: 0, x: x, z: z, y0: col.y0, y1: col.y1 };
    doors.push(d);
    return d;
  }

  /* ------------------------------------------------------------- models */
  /* size is the wanted height, unless axis is 'x' (flat things like rugs) */
  function place(key, x, y, z, size, rot, solid, axis) {
    var src = MODELS[key];
    if (!src) return null;
    var o = src.clone(true);
    var bb = new T.Box3().setFromObject(o);
    var sz = new T.Vector3(); bb.getSize(sz);
    var ref = (axis === 'x') ? Math.max(sz.x, sz.z) : sz.y;
    var s = size / Math.max(0.0001, ref);
    o.scale.setScalar(s);
    bb.setFromObject(o);
    o.position.set(-(bb.min.x + bb.max.x) / 2, -bb.min.y, -(bb.min.z + bb.max.z) / 2);
    var g = new T.Group();
    g.add(o);
    g.position.set(x, y, z);
    g.rotation.y = rot || 0;
    W.scene.add(g);
    if (solid) {
      var wb = new T.Box3().setFromObject(g);
      var ws = new T.Vector3(); wb.getSize(ws);
      var wc = new T.Vector3(); wb.getCenter(wc);
      W.addBox(wc.x, wc.y, wc.z, ws.x * 0.40, ws.y / 2, ws.z * 0.40, 0);
    }
    return g;
  }
  W.place = place;

  function loadModels(list, done) {
    loader = new T.GLTFLoader();
    var left = list.length;
    if (!left) { done(); return; }
    list.forEach(function (n) {
      loader.load('assets/models/' + n + '.glb', function (g) {
        g.scene.traverse(function (o) {
          if (o.isMesh) {
            o.castShadow = false; o.receiveShadow = false;
            if (o.material) {
              o.material.envMapIntensity = 0.35;
              if (o.material.map) o.material.map.anisotropy = 4;
            }
          }
        });
        MODELS[n] = g.scene;
        if (--left === 0) done();
      }, undefined, function () {
        W.diag('model missing: ' + n);
        if (--left === 0) done();
      });
    });
  }

  /* ---------------------------------------------------------- the town */
  var TOWN = { x: 0, z: 0, y: 0, R: 118 };

  function buildTown() {
    var R = TOWN.R, Y = TOWN.y;
    var N = 72;
    var segW = (2 * Math.PI * R) / N * 1.12;
    var gateA = Math.PI / 2;               /* south gate */
    for (var i = 0; i < N; i++) {
      var a = (i / N) * Math.PI * 2;
      var da = Math.abs(Math.atan2(Math.sin(a - gateA), Math.cos(a - gateA)));
      if (da < 0.075) continue;            /* the gateway gap */
      var x = TOWN.x + Math.cos(a) * R, z = TOWN.z + Math.sin(a) * R;
      box(segW, 9.5, 4.6, x, Y + 4.75, z, i % 2 ? M.stone : M.stone2, -a);
      /* crenellations */
      for (var k = -1; k <= 1; k++) {
        var cx = x + Math.cos(a - Math.PI / 2) * (k * segW * 0.33);
        var cz = z + Math.sin(a - Math.PI / 2) * (k * segW * 0.33);
        box(segW * 0.24, 1.15, 1.0, cx + Math.cos(a) * 1.7, Y + 10.1, cz + Math.sin(a) * 1.7, M.stone, -a, false);
      }
    }
    /* towers */
    for (var t = 0; t < 8; t++) {
      var ta = (t / 8) * Math.PI * 2 + 0.4;
      var tx = TOWN.x + Math.cos(ta) * R, tz = TOWN.z + Math.sin(ta) * R;
      cyl(6.4, 7.2, 15, 14, tx, Y + 7.5, tz, M.stone2);
      dome(6.6, tx, Y + 15, tz, M.stone, 18);
      finial(tx, Y + 19.6, tz, 1.1);
      torch(tx + Math.cos(ta) * 7.0, Y + 11.4, tz + Math.sin(ta) * 7.0, ta);
    }
    /* the great gate */
    var gx = TOWN.x + Math.cos(gateA) * R, gz = TOWN.z + Math.sin(gateA) * R;
    var gw = 9;
    cyl(5.2, 6.0, 19, 12, gx - 8.6, Y + 9.5, gz, M.stone2);
    cyl(5.2, 6.0, 19, 12, gx + 8.6, Y + 9.5, gz, M.stone2);
    dome(5.4, gx - 8.6, Y + 19, gz, M.stone, 16);
    dome(5.4, gx + 8.6, Y + 19, gz, M.stone, 16);
    finial(gx - 8.6, Y + 22.9, gz, 1); finial(gx + 8.6, Y + 22.9, gz, 1);
    box(gw + 7, 3.2, 5.0, gx, Y + 12.4, gz, M.stone);          /* lintel over the gate */
    arch(gw, 7.2, 5.2, gx, Y + 7.2, gz, M.stone2, 0);
    torch(gx - 5.4, Y + 3.4, gz + 2.7, 0);
    torch(gx + 5.4, Y + 3.4, gz + 2.7, 0);
    /* stairs to the rampart, both sides of the gate */
    [-1, 1].forEach(function (sgn) {
      var sx = gx + sgn * 17, sz = gz - 6;
      for (var s = 0; s < 14; s++) {
        box(3.4, 0.72, 1.5, sx + sgn * 0.0, Y + 0.36 + s * 0.68, sz - s * 1.42, M.stone2, 0);
      }
      box(3.4, 0.9, 3.0, sx, Y + 9.4, sz - 20.4, M.stone2, 0);
    });
    /* rampart walkway ring, just inside the wall */
    for (var wI = 0; wI < N; wI++) {
      var wa = (wI / N) * Math.PI * 2;
      var wx = TOWN.x + Math.cos(wa) * (R - 3.2), wz = TOWN.z + Math.sin(wa) * (R - 3.2);
      box(segW, 0.7, 2.6, wx, Y + 9.2, wz, M.stone2, -wa);
    }
  }

  /* the friday mosque · dome, minaret, mihrab, lamps */
  function buildMosque(cx, cz) {
    var Y = TOWN.y, w = 30, d = 30, h = 9, th = 1.2;
    var doorW = 3.6;
    /* walls with a doorway in the south face */
    box(w, h, th, cx, Y + h / 2, cz - d / 2, M.stone);
    box(th, h, d, cx - w / 2, Y + h / 2, cz, M.stone);
    box(th, h, d, cx + w / 2, Y + h / 2, cz, M.stone);
    var side = (w - doorW) / 2;
    box(side, h, th, cx - (doorW / 2 + side / 2), Y + h / 2, cz + d / 2, M.stone);
    box(side, h, th, cx + (doorW / 2 + side / 2), Y + h / 2, cz + d / 2, M.stone);
    box(doorW, h - 4.6, th, cx, Y + h - (h - 4.6) / 2, cz + d / 2, M.stone);
    arch(doorW + 0.6, 3.4, th + 0.5, cx, Y + 4.4, cz + d / 2, M.stone2, 0);
    door(cx - doorW / 2, Y, cz + d / 2, doorW, 4.3, 0, M.wood);

    /* roof and domes */
    box(w + 1.4, 0.8, d + 1.4, cx, Y + h + 0.4, cz, M.stone2);
    cyl(9.2, 9.6, 3.4, 24, cx, Y + h + 2.4, cz, M.stone2, false);
    dome(9.4, cx, Y + h + 4.0, cz, M.stone, 30);
    finial(cx, Y + h + 13.2, cz, 1.6);
    [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(function (q) {
      var qx = cx + q[0] * (w / 2 - 4), qz = cz + q[1] * (d / 2 - 4);
      dome(3.5, qx, Y + h + 0.8, qz, M.stone2, 18);
      finial(qx, Y + h + 4.1, qz, 0.8);
    });
    /* minaret */
    var mx = cx - w / 2 - 4.5, mz = cz - d / 2 - 4.5;
    cyl(2.3, 2.9, 30, 16, mx, Y + 15, mz, M.stone2);
    cyl(3.5, 3.5, 1.0, 16, mx, Y + 27.5, mz, M.stone, false);
    cyl(1.9, 2.2, 5, 14, mx, Y + 31, mz, M.stone2, false);
    dome(2.3, mx, Y + 33.4, mz, M.stone, 16);
    finial(mx, Y + 35.6, mz, 1);
    lamp(mx, Y + 28.4, mz, 1.7, false);

    /* interior */
    var fl = new T.Mesh(new T.PlaneGeometry(w - 2, d - 2), M.floor);
    fl.rotation.x = -Math.PI / 2; fl.position.set(cx, Y + 0.06, cz);
    W.scene.add(fl);
    /* mihrab niche in the qibla wall */
    box(3.0, 5.4, 1.0, cx, Y + 2.7, cz - d / 2 + 1.3, M.stone2, 0, false);
    arch(3.0, 2.6, 1.2, cx, Y + 5.2, cz - d / 2 + 1.3, M.gold, 0);
    /* columns */
    [[-8, -8], [8, -8], [-8, 8], [8, 8]].forEach(function (p) {
      cyl(0.75, 0.85, h - 0.4, 12, cx + p[0], Y + (h - 0.4) / 2, cz + p[1], M.stone2);
    });
    /* hanging lamps */
    [[-8, -8], [8, -8], [-8, 8], [8, 8], [0, 0]].forEach(function (p) {
      lamp(cx + p[0], Y + 4.6, cz + p[1], 1.5);
    });
    W.MOSQUE = { x: cx, z: cz, y: Y };
  }

  function buildPalace(cx, cz) {
    var Y = TOWN.y, w = 34, d = 24, h = 12, th = 1.2, doorW = 4.2;
    box(w, h, th, cx, Y + h / 2, cz - d / 2, M.brick);
    box(th, h, d, cx - w / 2, Y + h / 2, cz, M.brick);
    box(th, h, d, cx + w / 2, Y + h / 2, cz, M.brick);
    var side = (w - doorW) / 2;
    box(side, h, th, cx - (doorW / 2 + side / 2), Y + h / 2, cz + d / 2, M.brick);
    box(side, h, th, cx + (doorW / 2 + side / 2), Y + h / 2, cz + d / 2, M.brick);
    box(doorW, h - 5.4, th, cx, Y + h - (h - 5.4) / 2, cz + d / 2, M.brick);
    arch(doorW + 0.7, 3.6, th + 0.6, cx, Y + 5.1, cz + d / 2, M.stone2, 0);
    door(cx - doorW / 2, Y, cz + d / 2, doorW, 5.0, 0, M.wood);
    box(w + 1.6, 0.9, d + 1.6, cx, Y + h + 0.45, cz, M.brick2);
    cyl(7.4, 7.8, 2.6, 22, cx, Y + h + 2.2, cz, M.brick2, false);
    dome(7.6, cx, Y + h + 3.4, cz, M.stone, 26);
    finial(cx, Y + h + 10.6, cz, 1.4);
    [-11, 11].forEach(function (o) {
      dome(3.2, cx + o, Y + h + 0.9, cz, M.stone2, 18);
      finial(cx + o, Y + h + 3.9, cz, 0.8);
    });
    /* parapet teeth */
    for (var i = -1; i <= 1; i += 2) {
      for (var k = -w / 2 + 2; k < w / 2; k += 3.4) {
        box(1.5, 1.1, 1.0, cx + k, Y + h + 1.4, cz + i * (d / 2 + 0.3), M.brick2, 0, false);
      }
    }
    var fl = new T.Mesh(new T.PlaneGeometry(w - 2, d - 2), M.floor);
    fl.rotation.x = -Math.PI / 2; fl.position.set(cx, Y + 0.06, cz);
    W.scene.add(fl);
    [[-10, -6], [10, -6], [-10, 6], [10, 6]].forEach(function (p) {
      cyl(0.8, 0.9, h - 0.5, 12, cx + p[0], Y + (h - 0.5) / 2, cz + p[1], M.stone2);
      lamp(cx + p[0], Y + 5.2, cz + p[1], 1.4);
    });
    torch(cx - doorW - 1.4, Y + 3.0, cz + d / 2 + 0.8, 0);
    torch(cx + doorW + 1.4, Y + 3.0, cz + d / 2 + 0.8, 0);
    W.PALACE = { x: cx, z: cz, y: Y };
  }

  function buildLibrary(cx, cz) {
    var Y = TOWN.y, w = 20, d = 15, h = 7.5, th = 1.0, doorW = 3.2;
    box(w, h, th, cx, Y + h / 2, cz - d / 2, M.brick2);
    box(th, h, d, cx - w / 2, Y + h / 2, cz, M.brick2);
    box(th, h, d, cx + w / 2, Y + h / 2, cz, M.brick2);
    var side = (w - doorW) / 2;
    box(side, h, th, cx - (doorW / 2 + side / 2), Y + h / 2, cz + d / 2, M.brick2);
    box(side, h, th, cx + (doorW / 2 + side / 2), Y + h / 2, cz + d / 2, M.brick2);
    box(doorW, h - 4.2, th, cx, Y + h - (h - 4.2) / 2, cz + d / 2, M.brick2);
    arch(doorW + 0.5, 2.8, th + 0.4, cx, Y + 4.0, cz + d / 2, M.stone2, 0);
    door(cx - doorW / 2, Y, cz + d / 2, doorW, 3.9, 0, M.wood);
    box(w + 1.2, 0.7, d + 1.2, cx, Y + h + 0.35, cz, M.brick);
    for (var k = -w / 2 + 1.6; k < w / 2; k += 3.0) {
      box(1.3, 0.9, 0.9, cx + k, Y + h + 1.1, cz + d / 2 + 0.2, M.brick, 0, false);
      box(1.3, 0.9, 0.9, cx + k, Y + h + 1.1, cz - d / 2 - 0.2, M.brick, 0, false);
    }
    var fl = new T.Mesh(new T.PlaneGeometry(w - 2, d - 2), M.floor);
    fl.rotation.x = -Math.PI / 2; fl.position.set(cx, Y + 0.06, cz);
    W.scene.add(fl);
    /* shelves of books along the walls */
    for (var s = -1; s <= 1; s += 2) {
      for (var b = -w / 2 + 3; b < w / 2 - 2; b += 2.4) {
        box(2.1, 3.4, 0.7, cx + b, Y + 1.7, cz + s * (d / 2 - 1.2), M.wood, 0);
        for (var r = 0; r < 3; r++) {
          box(1.9, 0.55, 0.5, cx + b, Y + 0.72 + r * 1.05, cz + s * (d / 2 - 1.05), M.dark, 0, false);
        }
      }
    }
    lamp(cx, Y + 4.4, cz, 1.5);
    lamp(cx - 6, Y + 4.4, cz, 1.2);
    lamp(cx + 6, Y + 4.4, cz, 1.2);
    W.LIBRARY = { x: cx, z: cz, y: Y };
  }

  /* mudbrick homes with lit windows; some open */
  function buildHouses() {
    var Y = TOWN.y;
    var spots = [
      [-72, 18, 0.3], [-58, 44, -0.5], [-30, 62, 0.9], [4, 74, 0.2], [36, 62, -0.7],
      [64, 40, 0.5], [76, 8, -0.2], [66, -26, 0.8], [-74, -18, -0.6], [-62, -48, 0.4],
      [-26, -74, 0.15], [16, -78, -0.4], [52, -62, 0.7], [86, -6, 0.1], [-88, 6, -0.3],
      [-44, 84, 0.6], [30, 92, -0.25], [-8, -96, 0.35]
    ];
    spots.forEach(function (s, i) {
      var w = 7 + (i % 3) * 1.6, d = 6 + (i % 4) * 1.2, h = 3.6 + (i % 3) * 1.5;
      var x = s[0], z = s[1], rot = s[2];
      var m = i % 2 ? M.brick : M.brick2;
      /* hollow if the door opens, solid block otherwise */
      var opens = (i % 4 === 0);
      if (opens) {
        var th = 0.5, doorW = 1.6;
        box(w, h, th, x, Y + h / 2, z - d / 2, m, rot);
        box(th, h, d, x - w / 2, Y + h / 2, z, m, rot);
        box(th, h, d, x + w / 2, Y + h / 2, z, m, rot);
        var side = (w - doorW) / 2;
        box(side, h, th, x - (doorW / 2 + side / 2), Y + h / 2, z + d / 2, m, rot);
        box(side, h, th, x + (doorW / 2 + side / 2), Y + h / 2, z + d / 2, m, rot);
        box(doorW, h - 2.2, th, x, Y + h - (h - 2.2) / 2, z + d / 2, m, rot);
        door(x - doorW / 2, Y, z + d / 2, doorW, 2.1, rot, M.wood);
        var fl = new T.Mesh(new T.PlaneGeometry(w - 1.2, d - 1.2), M.floor);
        fl.rotation.x = -Math.PI / 2; fl.position.set(x, Y + 0.05, z);
        W.scene.add(fl);
        lamp(x, Y + h - 0.9, z, 1.1);
      } else {
        box(w, h, d, x, Y + h / 2, z, m, rot);
        var dq = new T.Mesh(new T.PlaneGeometry(1.5, 2.1), M.wood);
        dq.position.set(x + Math.sin(rot + Math.PI / 2) * 0.02, Y + 1.05, z + d / 2 + 0.03);
        dq.rotation.y = rot;
        W.scene.add(dq);
      }
      box(w + 0.5, 0.5, d + 0.5, x, Y + h + 0.25, z, m, rot);
      for (var k = -1; k <= 1; k++) {
        box(1.0, 0.7, 0.7, x + k * (w * 0.3), Y + h + 0.85, z + d / 2 * 0.9, m, rot, false);
      }
      var win = new T.Mesh(new T.PlaneGeometry(0.75, 0.95), (i % 3) ? M.win : M.winOff);
      win.position.set(x - w * 0.28, Y + h * 0.62, z + d / 2 + 0.04);
      win.rotation.y = rot;
      W.scene.add(win);
      if (i % 3 === 0) lamp(x - w * 0.28, Y + h * 0.62, z + d / 2 + 0.5, 0.55, false);
      if (i % 5 === 0) torch(x + w / 2 + 0.5, Y + 2.6, z + d / 2 + 0.4, rot);
    });
  }

  /* a desert camp: open tents around a fire */
  function buildCamp(cx, cz, n) {
    var Y = W.heightAt(cx, cz);
    W.addFlat(cx, cz, 16, Y, 22);
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2 + 0.4;
      var tx = cx + Math.cos(a) * 9.5, tz = cz + Math.sin(a) * 9.5;
      var ty = Y;
      /* four poles and a slanted canopy, open to the fire */
      var ph = 2.5;
      [[-3, -2.6], [3, -2.6], [-3.4, 2.8], [3.4, 2.8]].forEach(function (p, k) {
        var px = tx + p[0] * Math.cos(a) - p[1] * Math.sin(a);
        var pz = tz + p[0] * Math.sin(a) + p[1] * Math.cos(a);
        cyl(0.09, 0.11, k < 2 ? ph : ph * 0.72, 6, px, ty + (k < 2 ? ph : ph * 0.72) / 2, pz, M.wood);
      });
      var canopy = new T.Mesh(new T.PlaneGeometry(7.2, 6.4, 6, 6), M.cloth);
      var cp = canopy.geometry.attributes.position;
      for (var v = 0; v < cp.count; v++) {
        var vx = cp.getX(v), vy = cp.getY(v);
        cp.setZ(v, Math.sin(vx * 0.9) * 0.16 + Math.cos(vy * 1.1) * 0.14);
      }
      canopy.geometry.computeVertexNormals();
      canopy.material.side = T.DoubleSide;
      canopy.rotation.set(-Math.PI / 2 + 0.24, 0, 0);
      canopy.position.set(tx, ty + ph - 0.25, tz);
      canopy.rotation.y = 0;
      var wrap = new T.Group(); wrap.add(canopy);
      wrap.position.set(0, 0, 0);
      canopy.position.set(tx, ty + ph - 0.2, tz);
      W.scene.add(canopy);
      /* back wall of cloth */
      var back = new T.Mesh(new T.PlaneGeometry(7.0, 2.2), M.cloth);
      back.material.side = T.DoubleSide;
      var bx = tx + Math.cos(a) * 2.7, bz = tz + Math.sin(a) * 2.7;
      back.position.set(bx, ty + 1.1, bz);
      back.rotation.y = -a + Math.PI / 2;
      W.scene.add(back);
      /* rug under the tent */
      if (MODELS.carpet) place('carpet', tx, ty + 0.03, tz, 3.2, a, false, 'x');
    }
    /* the campfire, ringed with stones */
    for (var s = 0; s < 9; s++) {
      var sa = (s / 9) * Math.PI * 2;
      cyl(0.28, 0.34, 0.4, 6, cx + Math.cos(sa) * 1.25, Y + 0.16, cz + Math.sin(sa) * 1.25, M.stone2, false);
    }
    for (var lg = 0; lg < 4; lg++) {
      var la = (lg / 4) * Math.PI;
      var log = new T.Mesh(new T.CylinderGeometry(0.11, 0.13, 1.5, 6), M.wood);
      log.position.set(cx, Y + 0.22, cz);
      log.rotation.z = Math.PI / 2 - 0.28;
      log.rotation.y = la;
      W.scene.add(log);
    }
    fire(cx, Y + 0.3, cz, 2.0, 2.6);
    return { x: cx, z: cz, y: Y };
  }

  /* a cave mouth in the rocks, lit from within */
  function buildCave(cx, cz) {
    var Y = W.heightAt(cx, cz);
    W.addFlat(cx, cz, 14, Y, 26);
    var R = 13, H = 8.5;
    /* a ring of rock walls with one opening = the mouth */
    var N = 26;
    for (var i = 0; i < N; i++) {
      var a = (i / N) * Math.PI * 2;
      if (Math.abs(Math.atan2(Math.sin(a - Math.PI / 2), Math.cos(a - Math.PI / 2))) < 0.22) continue;
      var x = cx + Math.cos(a) * R, z = cz + Math.sin(a) * R;
      var hh = H + Math.sin(i * 1.7) * 1.4;
      box(R * 2 * Math.PI / N * 1.3, hh, 4.6, x, Y + hh / 2, z, M.stone2, -a);
    }
    /* roof slab and boulders piled on it */
    var roof = new T.Mesh(new T.CylinderGeometry(R + 2.6, R + 1.2, 3.2, 16), M.stone2);
    roof.position.set(cx, Y + H + 1.2, cz);
    W.scene.add(roof);
    W.addBox(cx, Y + H + 1.2, cz, R + 1.0, 1.6, R + 1.0, 0);
    for (var b = 0; b < 7; b++) {
      var ba = b * 1.7;
      var key = ['rock_a', 'rock_b', 'rock_c'][b % 3];
      if (MODELS[key]) place(key, cx + Math.cos(ba) * (R * 0.55), Y + H + 2.6, cz + Math.sin(ba) * (R * 0.55), 3 + (b % 3), ba);
    }
    /* mouth arch */
    arch(7, 5.2, 5.0, cx, Y + 5.0, cz + R, M.stone2, 0);
    /* inside: floor, torches, a pool of light */
    var fl = new T.Mesh(new T.CircleGeometry(R - 1, 24), M.floor);
    fl.rotation.x = -Math.PI / 2; fl.position.set(cx, Y + 0.05, cz);
    W.scene.add(fl);
    torch(cx - 5.5, Y + 2.6, cz - 3, 0.6);
    torch(cx + 5.5, Y + 2.6, cz - 3, -0.6);
    fire(cx, Y + 0.25, cz - 6, 1.5, 1.8);
    if (MODELS.carpet) place('carpet', cx, Y + 0.06, cz - 4.4, 3.4, 0.3, false, 'x');
    if (MODELS.mashaf) place('mashaf', cx, Y + 0.2, cz - 4.4, 0.42, 0.3, false, 'x');
    return { x: cx, z: cz, y: Y };
  }

  /* an oasis: water, palms, big trees, flowers */
  function buildOasis(cx, cz) {
    var Y = W.heightAt(cx, cz);
    for (var i = 0; i < 22; i++) {
      var a = (i / 22) * Math.PI * 2 + Math.sin(i) * 0.3;
      var r = 26 + ((i * 37) % 19);
      var x = cx + Math.cos(a) * r, z = cz + Math.sin(a) * r;
      var y = W.heightAt(x, z);
      if (y < W.WATER_Y + 0.2) continue;
      if (MODELS.palm) place('palm', x, y - 0.2, z, 9 + (i % 5) * 1.6, a * 2.1);
    }
    for (var t = 0; t < 5; t++) {
      var ta = t * 1.35 + 0.7, tr = 44 + (t % 3) * 9;
      var tx = cx + Math.cos(ta) * tr, tz = cz + Math.sin(ta) * tr;
      var ty = W.heightAt(tx, tz);
      if (ty < W.WATER_Y + 0.3) continue;
      var key = ['tree_big_a', 'tree_big_b', 'tree_anc'][t % 3];
      if (MODELS[key]) place(key, tx, ty - 0.3, tz, 17 + (t % 3) * 7, ta);
    }
    return { x: cx, z: cz, y: Y };
  }

  /* -------------------------------------------------- growing the world */
  function firstMesh(root) {
    var found = null;
    root.traverse(function (o) { if (!found && o.isMesh) found = o; });
    return found;
  }
  var VEG = {};
  function vegSource(key) {
    if (VEG[key]) return VEG[key];          /* never cache a miss */
    var src = MODELS[key];
    if (!src) return null;
    var m = firstMesh(src);
    if (!m) return null;
    var g = m.geometry.clone();
    /* normalise so instances stand on the ground at unit height */
    g.computeBoundingBox();
    var bb = g.boundingBox, sz = new T.Vector3(); bb.getSize(sz);
    var s = 1 / Math.max(0.0001, sz.y);
    g.translate(-(bb.min.x + bb.max.x) / 2, -bb.min.y, -(bb.min.z + bb.max.z) / 2);
    g.scale(s, s, s);
    var mm = m.material.clone();
    mm.side = T.DoubleSide;
    if (mm.map) mm.map.anisotropy = 4;
    mm.metalness = 0;
    if (mm.transparent || mm.alphaMap || (mm.map && mm.alphaTest === 0)) { mm.alphaTest = 0.42; mm.transparent = false; }
    windify(mm, 0.055);
    return (VEG[key] = { g: g, m: mm });
  }

  /* a calm wind, bending everything that grows */
  function windify(m, amp) {
    m.onBeforeCompile = function (sh) {
      sh.uniforms.uWind = { value: 0 };
      winds.push(sh.uniforms.uWind);
      sh.vertexShader = 'uniform float uWind;\n' + sh.vertexShader.replace(
        '#include <begin_vertex>',
        ['#include <begin_vertex>',
          'float wh = clamp(transformed.y, 0.0, 3.0);',
          '#ifdef USE_INSTANCING',
          'float wsd = instanceMatrix[3].x * 0.21 + instanceMatrix[3].z * 0.17;',
          '#else',
          'float wsd = 0.0;',
          '#endif',
          'transformed.x += ' + amp + ' * wh * wh * (sin(uWind * 1.1 + wsd) * 0.66 + sin(uWind * 0.47 + wsd * 1.9) * 0.34);',
          'transformed.z += ' + amp + ' * 0.62 * wh * wh * sin(uWind * 0.83 + wsd * 1.4);'
        ].join('\n'));
    };
    return m;
  }
  W.windify = windify;

  function rng(a, b, c) {
    var n = Math.sin(a * 12.9898 + b * 78.233 + c * 37.719) * 43758.5453;
    return n - Math.floor(n);
  }

  /* what grows in one chunk */
  W.scatter = function (W, ci, cj, CH) {
    var out = [];
    var ox = ci * CH, oz = cj * CH;
    var dummy = new T.Object3D();

    function sow(key, count, pick, scaleMin, scaleMax) {
      var src = vegSource(key);
      if (!src || count <= 0) return;
      var im = new T.InstancedMesh(src.g, src.m, count);
      var n = 0;
      for (var i = 0; i < count; i++) {
        var rx = ox + rng(ci * 7 + i, cj * 13, 1.7) * CH;
        var rz = oz + rng(ci * 3 + i, cj * 11, 5.3) * CH;
        var h = W.heightAt(rx, rz);
        if (!pick(rx, rz, h)) continue;
        var s = scaleMin + rng(i, ci + cj, 9.1) * (scaleMax - scaleMin);
        dummy.position.set(rx, h - 0.04, rz);
        dummy.rotation.set(0, rng(i, ci, 2.2) * 6.283, 0);
        dummy.scale.set(s, s, s);
        dummy.updateMatrix();
        im.setMatrixAt(n++, dummy.matrix);
      }
      if (!n) { im.dispose(); return; }
      im.count = n;
      im.instanceMatrix.needsUpdate = true;
      im.frustumCulled = true;
      W.scene.add(im);
      out.push(im);
    }

    var cb = W.biomeAt(ox + CH / 2, oz + CH / 2);
    var lush = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.25 && w.g > 0.45 && w.r < 0.4;
    };
    var dry = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.6 && w.g < 0.5;
    };
    var stony = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.4 && w.r > 0.35;
    };

    sow('grass_a', Math.round(140 * (0.25 + cb.grass)), lush, 0.5, 1.15);
    sow('grass_b', Math.round(90 * (0.2 + cb.grass)), lush, 0.4, 0.9);
    sow('fl_orange', Math.round(34 * cb.grass), lush, 0.35, 0.7);
    sow('fl_yellow', Math.round(30 * cb.grass), lush, 0.3, 0.6);
    sow('fl_purple', Math.round(26 * cb.grass), lush, 0.3, 0.6);
    sow('fl_white', Math.round(22 * cb.grass), lush, 0.3, 0.6);
    sow('bush_dry', Math.round(16 * (1 - cb.grass)), dry, 0.9, 2.0);
    sow('rock_small', 10, dry, 0.6, 1.8);
    sow('rock_d', Math.round(9 * (0.3 + cb.rock)), stony, 1.0, 3.2);

    /* trees and palms, sparse and deliberate */
    var treeN = Math.round(5 * cb.grass + 1);
    for (var t = 0; t < treeN; t++) {
      var tx = ox + rng(ci + t, cj, 3.9) * CH, tz = oz + rng(ci, cj + t, 8.4) * CH;
      var th = W.heightAt(tx, tz);
      var w = W.groundWeights(tx, tz, th);
      if (th < W.WATER_Y + 0.5) continue;
      var key = null, sc = 1;
      if (w.g > 0.62) {
        var pickN = rng(tx, tz, 1.1);
        key = pickN > 0.86 ? 'tree_anc' : (pickN > 0.5 ? 'tree_big_a' : 'tree_big_b');
        sc = pickN > 0.86 ? (24 + rng(tx, tz, 4) * 14) : (11 + rng(tx, tz, 2) * 8);
      } else if (w.w > 0.35) {
        key = 'palm'; sc = 8 + rng(tx, tz, 7) * 5;
      } else if (rng(tx, tz, 6.6) > 0.72) {
        key = 'tree_small'; sc = 4 + rng(tx, tz, 5) * 3;
      }
      if (!key || !MODELS[key]) continue;
      var g = place(key, tx, th - 0.25, tz, sc, rng(tx, tz, 9) * 6.283);
      if (g) out.push(g);
    }
    /* boulders that you cannot walk through */
    for (var b = 0; b < 3; b++) {
      var bx = ox + rng(ci + b * 3, cj, 2.6) * CH, bz = oz + rng(ci, cj + b * 5, 6.1) * CH;
      var bh = W.heightAt(bx, bz);
      var bw = W.groundWeights(bx, bz, bh);
      if (bh < W.WATER_Y + 1 || bw.r < 0.3) continue;
      var bk = ['rock_a', 'rock_b', 'rock_c'][b % 3];
      if (!MODELS[bk]) continue;
      var bg = place(bk, bx, bh - 0.4, bz, 2.4 + rng(bx, bz, 3) * 5.5, rng(bx, bz, 4) * 6.283);
      if (bg) out.push(bg);
    }
    return out;
  };

  /* ------------------------------------------------------- interaction */
  W.interact = function (W) {
    var p = W.getPos();
    var best = null, bd = 3.4;
    for (var i = 0; i < doors.length; i++) {
      var d = doors[i];
      var dist = Math.hypot(p.x - d.x, p.z - d.z);
      if (dist < bd) { bd = dist; best = d; }
    }
    if (best) {
      best.open = !best.open;
      if (best.open) { best.col.y1 = best.col.y0; } else { best.col.y1 = best.y1; }
    }
  };

  W.tick = function (W, dt, t) {
    for (var i = 0; i < winds.length; i++) winds[i].value = t;
    var cp = W.cam.position;
    driveLights(t);
    var flameFrame = 1 - (Math.floor((t * 15) % 8) + 1) / 8;
    for (var q = 0; q < flameTex.length; q++) flameTex[q].offset.y = 1 - (Math.floor((t * 15 + q * 2.7) % 8) + 1) / 8;
    for (var f = 0; f < fires.length; f++) {
      var fr = fires[f];
      if (fr.d2 > 26000) { fr.m.visible = false; fr.core.visible = false; continue; }
      fr.m.visible = true; fr.core.visible = true;
      fr.m.lookAt(cp.x, fr.m.position.y, cp.z);
      fr.core.lookAt(cp.x, fr.core.position.y, cp.z);
      fr.core.material.opacity = 0.30 + 0.22 * fr.lit;
      fr.m.scale.set(0.94 + 0.12 * fr.lit, 0.9 + 0.2 * fr.lit, 1);
    }
    for (var l = 0; l < lamps.length; l++) {
      var lp = lamps[l];
      if (lp.d2 > 26000) { lp.g.visible = false; continue; }
      lp.g.visible = true;
      lp.g.lookAt(cp);
      lp.g.material.opacity = 0.5 + 0.16 * lp.lit;
    }
    for (var d2 = 0; d2 < doors.length; d2++) {
      var dr = doors[d2];
      var target = dr.open ? -1.95 : 0;
      dr.ang += (target - dr.ang) * Math.min(1, dt * 4.6);
      dr.pivot.rotation.y = dr.rot0 === undefined ? (dr.rot0 = dr.pivot.rotation.y) + dr.ang : dr.rot0 + dr.ang;
    }
  };

  /* ------------------------------------------------------------- build */
  W.buildAll = function (W) {
    initMats();
    initFire();
    initPool();

    var baseY = W.heightAt(TOWN.x, TOWN.z);
    TOWN.y = Math.max(baseY, W.WATER_Y + 7);
    W.addFlat(TOWN.x, TOWN.z, TOWN.R + 42, TOWN.y, 120);

    W.SPAWN = { x: 0, z: TOWN.R + 46 };
    W.SPAWN_YAW = 0;
    W.SHOTS = {
      '1': { x: 0, z: TOWN.R + 70, yaw: 0, pitch: -0.02, h: 2.4 },
      '2': { x: 2, z: 40, yaw: 0.62, pitch: -0.02 },
      '3': { x: 0, z: TOWN.R - 4, yaw: 3.14, pitch: -0.12, h: 11.6 },
      '4': { x: 300, z: 396, yaw: 3.14, pitch: -0.03 },
      '5': { x: 430, z: -244, yaw: 3.14, pitch: -0.05 },
      '6': { x: -360, z: 268, yaw: 3.14, pitch: -0.02 },
      '7': { x: -34, z: 2, yaw: 3.14, pitch: 0.05 },
      '8': { x: 60, z: 300, yaw: 2.2, pitch: -0.16, h: 130, fly: true }
    };

    buildTown();
    buildMosque(-34, -30);
    buildPalace(36, -34);
    buildLibrary(34, 36);
    buildHouses();

    loadModels(['palm', 'lantern', 'quran', 'mashaf', 'carpet', 'well', 'doors',
      'tree_big_a', 'tree_big_b', 'tree_anc', 'tree_small', 'bush_dry',
      'fl_orange', 'fl_yellow', 'fl_purple', 'fl_white',
      'grass_a', 'grass_b', 'rock_a', 'rock_b', 'rock_c', 'rock_d', 'rock_small',
      'house_a', 'house_b', 'house_c', 'kasbah'], function () {
        /* things that need the models */
        if (MODELS.well) place('well', 6, TOWN.y, 8, 3.2, 0.4, true);
        lamp(6, TOWN.y + 3.4, 8, 1.3, false);
        if (MODELS.house_a) place('house_a', -86, TOWN.y, -70, 11, 0.6, true);
        if (MODELS.house_b) place('house_b', 84, TOWN.y, 62, 11, -0.9, true);
        if (MODELS.house_c) place('house_c', -6, TOWN.y, -84, 10, 0.2, true);

        buildCamp(430, -260, 4);
        buildCamp(-520, 300, 3);
        buildCave(-360, 250);
        buildOasis(300, 330);

        if (W.refreshVeg) W.refreshVeg();
      });
  };
})();
