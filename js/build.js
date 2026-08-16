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

  /* every face gets the same brick size, whatever the wall's dimensions */
  var TILE = 2.6;
  function uvScaleBox(geo, w, h, d) {
    var uv = geo.attributes.uv;
    var pairs = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
    for (var f = 0; f < 6; f++) {
      var su = pairs[f][0] / TILE, sv = pairs[f][1] / TILE;
      for (var i = 0; i < 4; i++) {
        var k = f * 4 + i;
        uv.setXY(k, uv.getX(k) * su, uv.getY(k) * sv);
      }
    }
    uv.needsUpdate = true;
    return geo;
  }

  /* a solid box: drawn and collided */
  function box(w, h, d, x, y, z, m, rot, solid) {
    var g = new T.Mesh(uvScaleBox(new T.BoxGeometry(w, h, d), w, h, d), m || M.brick);
    g.position.set(x, y, z);
    if (rot) g.rotation.y = rot;
    W.scene.add(g);
    if (solid !== false) W.addBox(x, y, z, w / 2, h / 2, d / 2, rot || 0);
    return g;
  }
  function cyl(rt, rb, h, seg, x, y, z, m, solid) {
    var cg = new T.CylinderGeometry(rt, rb, h, seg);
    var cuv = cg.attributes.uv;
    for (var ci = 0; ci < cuv.count; ci++) {
      cuv.setXY(ci, cuv.getX(ci) * (2 * Math.PI * Math.max(rt, rb) / TILE), cuv.getY(ci) * (h / TILE));
    }
    cuv.needsUpdate = true;
    var g = new T.Mesh(cg, m || M.stone);
    g.position.set(x, y, z);
    W.scene.add(g);
    if (solid !== false) W.addBox(x, y, z, Math.max(rt, rb) * 0.86, h / 2, Math.max(rt, rb) * 0.86, 0);
    return g;
  }
  function dome(r, x, y, z, m, seg) {
    var dg = new T.SphereGeometry(r, seg || 26, Math.max(10, (seg || 26) / 2), 0, Math.PI * 2, 0, Math.PI * 0.52);
    var duv = dg.attributes.uv;
    for (var di = 0; di < duv.count; di++) {
      duv.setXY(di, duv.getX(di) * (2 * Math.PI * r / TILE), duv.getY(di) * (Math.PI * r * 0.5 / TILE));
    }
    duv.needsUpdate = true;
    var g = new T.Mesh(dg, m || M.stone);
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
      var bw = (Math.PI * w / 2) / steps * 1.55;
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
      g.userData.col = W.addBox(wc.x, wc.y, wc.z, ws.x * 0.40, ws.y / 2, ws.z * 0.40, 0);
    }
    return g;
  }
  W.place = place;

  /* models arrive a few at a time, and a failure is retried before giving up */
  function loadModels(list, done) {
    loader = new T.GLTFLoader();
    var queue = list.slice(), active = 0, left = list.length, MAX = 4;
    var loadEl = document.getElementById('load');

    function finish() {
      if (--left === 0) {
        if (loadEl) loadEl.style.display = 'none';
        done();
      } else if (loadEl && loadEl.style.display !== 'none') {
        loadEl.textContent = 'Building the world… ' + Math.round((1 - left / list.length) * 100) + '%';
      }
      pump();
    }

    function fetchOne(name, tries) {
      active++;
      loader.load('assets/models/' + name + '.glb', function (g) {
        active--;
        g.scene.traverse(function (o) {
          if (o.isMesh) {
            o.castShadow = false; o.receiveShadow = false;
            if (o.material) {
              o.material.envMapIntensity = 0.35;
              if (o.material.map) o.material.map.anisotropy = 4;
            }
          }
        });
        if (name.indexOf('house_') === 0 || name === 'kasbah') {
          g.scene.traverse(function (o) {
            if (o.isMesh && o.material && o.material.color) o.material.color.multiplyScalar(1.0).lerp(new T.Color(0xd8b98d), 0.34);
          });
        }
        MODELS[name] = g.scene;
        finish();
      }, undefined, function () {
        active--;
        if (tries < 2) { setTimeout(function () { fetchOne(name, tries + 1); }, 500 + tries * 900); }
        else { W.diag('model missing: ' + name); finish(); }
      });
    }

    function pump() {
      while (active < MAX && queue.length) fetchOne(queue.shift(), 0);
    }
    if (!left) { done(); return; }
    pump();
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
      var tx = cx + Math.cos(a) * 10.5, tz = cz + Math.sin(a) * 10.5;
      var g = new T.Group();
      g.position.set(tx, Y, tz);
      g.rotation.y = -a + Math.PI / 2;   /* the open side faces the fire */
      W.scene.add(g);

      var W2 = 7.0, D2 = 5.6, front = 2.55, back = 1.55;
      /* poles */
      [[-W2 / 2, -D2 / 2, front], [W2 / 2, -D2 / 2, front],
       [-W2 / 2, D2 / 2, back], [W2 / 2, D2 / 2, back]].forEach(function (p2) {
        var pole = new T.Mesh(new T.CylinderGeometry(0.075, 0.095, p2[2], 6), M.wood);
        pole.position.set(p2[0], p2[2] / 2, p2[1]);
        g.add(pole);
      });
      /* ridge pole across the open front */
      var ridge = new T.Mesh(new T.CylinderGeometry(0.06, 0.06, W2, 6), M.wood);
      ridge.rotation.z = Math.PI / 2;
      ridge.position.set(0, front, -D2 / 2);
      g.add(ridge);

      /* the goat-hair roof, sagging between its poles */
      var roof = new T.PlaneGeometry(W2, D2, 8, 6);
      var rp = roof.attributes.position;
      for (var v = 0; v < rp.count; v++) {
        var ux = rp.getX(v) / W2 + 0.5, uy = rp.getY(v) / D2 + 0.5;
        var lift = front + (back - front) * uy;
        var sag = -Math.sin(ux * Math.PI) * 0.22 * (0.4 + uy);
        rp.setZ(v, lift + sag);
      }
      roof.rotateX(-Math.PI / 2);
      roof.computeVertexNormals();
      var roofM = new T.Mesh(roof, M.cloth);
      roofM.material.side = T.DoubleSide;
      g.add(roofM);

      /* back wall and one side, leaving the front open */
      var back1 = new T.Mesh(new T.PlaneGeometry(W2, back), M.cloth);
      back1.material.side = T.DoubleSide;
      back1.position.set(0, back / 2, D2 / 2);
      g.add(back1);
      var side1 = new T.Mesh(new T.PlaneGeometry(D2, back * 0.92), M.cloth);
      side1.material.side = T.DoubleSide;
      side1.rotation.y = Math.PI / 2;
      side1.position.set(-W2 / 2, back * 0.46, 0);
      g.add(side1);

      /* guy ropes */
      [[-W2 / 2, -D2 / 2 - 1.5], [W2 / 2, -D2 / 2 - 1.5]].forEach(function (r2) {
        var rope = new T.Mesh(new T.CylinderGeometry(0.02, 0.02, 3.0, 4), M.dark);
        rope.position.set(r2[0] * 0.92, front * 0.55, (r2[1] + (-D2 / 2)) / 2 + 0.6);
        rope.rotation.x = 0.85;
        g.add(rope);
      });

      W.addBox(tx, Y + 1.2, tz, 3.6, 1.2, 2.9, -a + Math.PI / 2);
      if (MODELS.carpet) place('carpet', tx, Y + 0.04, tz, 3.0, -a + Math.PI / 2, false, 'x');
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

  /* a cave mouth in the rock, lit from within */
  function buildCave(cx, cz) {
    var Y = W.heightAt(cx, cz);
    W.addFlat(cx, cz, 16, Y, 34);
    var R = 13.5, H = 8.5;

    /* the cavity: dark rock seen from inside, so it reads as depth */
    var caveIn = new T.MeshStandardMaterial({ map: W.tex('assets/g_rock_d.jpg', true, true), color: 0x6d6152, roughness: 1, side: T.BackSide });
    var inner = new T.Mesh(new T.CylinderGeometry(R - 1.2, R - 0.6, H, 22, 1, true), caveIn);
    inner.position.set(cx, Y + H / 2, cz);
    W.scene.add(inner);
    var roof = new T.Mesh(new T.SphereGeometry(R - 0.8, 20, 10, 0, Math.PI * 2, 0, Math.PI * 0.5), caveIn);
    roof.scale.set(1, 0.42, 1);
    roof.position.set(cx, Y + H - 0.6, cz);
    W.scene.add(roof);

    /* the mound: boulders heaped into a hill, with a gap for the mouth */
    var N = 20;
    for (var i = 0; i < N; i++) {
      var a = (i / N) * Math.PI * 2;
      var toMouth = Math.abs(Math.atan2(Math.sin(a - Math.PI / 2), Math.cos(a - Math.PI / 2)));
      if (toMouth < 0.50) continue;
      var key = ['rock_a', 'rock_b', 'rock_c'][i % 3];
      if (!MODELS[key]) continue;
      var rr = R + 1.0 + ((i * 31) % 5) * 0.4;
      var sc = 10 + ((i * 17) % 6);
      place(key, cx + Math.cos(a) * rr, Y - 1.6, cz + Math.sin(a) * rr, sc, a * 1.7);
      W.addBox(cx + Math.cos(a) * rr, Y + H / 2, cz + Math.sin(a) * rr, 3.4, H / 2 + 2, 3.4, 0);
    }
    for (var b = 0; b < 8; b++) {
      var ba = b * 1.62, br = R * (0.22 + 0.42 * ((b * 13) % 5) / 5);
      var k2 = ['rock_b', 'rock_a', 'rock_c'][b % 3];
      if (MODELS[k2]) place(k2, cx + Math.cos(ba) * br, Y + H - 3.4 + (b % 3) * 0.7, cz + Math.sin(ba) * br, 7 + (b % 3) * 2.4, ba);
    }
    W.addBox(cx, Y + H + 2.2, cz, R * 0.8, 2.4, R * 0.8, 0);
    if (MODELS.rock_c) place('rock_c', cx - 10.5, Y - 1.2, cz + R - 1.5, 9, 0.6);
    if (MODELS.rock_a) place('rock_a', cx + 10.5, Y - 1.2, cz + R - 1.5, 8.5, 2.4);
    if (MODELS.rock_b) place('rock_b', cx, Y + 6.2, cz + R + 0.4, 7, 1.1);

    var fl = new T.Mesh(new T.CircleGeometry(R - 1.4, 24), M.floor);
    fl.rotation.x = -Math.PI / 2; fl.position.set(cx, Y + 0.05, cz);
    W.scene.add(fl);
    torch(cx - 5.6, Y + 2.7, cz - 2.5, 0.6);
    torch(cx + 5.6, Y + 2.7, cz - 2.5, -0.6);
    fire(cx, Y + 0.25, cz - 6.0, 1.5, 1.8);
    if (MODELS.carpet) place('carpet', cx, Y + 0.06, cz - 4.2, 3.4, 0.3, false, 'x');
    if (MODELS.mashaf) place('mashaf', cx, Y + 0.2, cz - 4.2, 0.42, 0.3, false, 'x');
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
    /* these are modelled at real size · keep their proportions, just plant them */
    m.updateWorldMatrix(true, false);
    g.applyMatrix4(m.matrixWorld);
    g.computeBoundingBox();
    var bb = g.boundingBox;
    g.translate(-(bb.min.x + bb.max.x) / 2, -bb.min.y, -(bb.min.z + bb.max.z) / 2);
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

  function hashU(n) {
    n = (n ^ 61) ^ (n >>> 16);
    n = (n + (n << 3)) | 0;
    n = n ^ (n >>> 4);
    n = Math.imul(n, 0x27d4eb2d);
    n = n ^ (n >>> 15);
    return (n >>> 0) / 4294967296;
  }
  function rng(a, b, c) {
    var n = (Math.round(a * 131) * 73856093) ^ (Math.round(b * 131) * 19349663) ^ (Math.round(c * 977) * 83492791);
    return hashU(n | 0);
  }

  /* what grows in one chunk */
  W.scatter = function (W, ci, cj, CH) {
    var out = [];
    var ox = ci * CH, oz = cj * CH;
    var dummy = new T.Object3D();

    function sow(key, count, pick, scaleMin, scaleMax) {
      count = Math.round(count * (W.vegScale || 1));
      var src = vegSource(key);
      if (!src || count <= 0) return;
      var im = new T.InstancedMesh(src.g, src.m, count);
      var n = 0;
      var salt = key.charCodeAt(0) * 7919 + key.length * 104729;
      for (var i = 0; i < count; i++) {
        var sd = (ci * 73856093) ^ (cj * 19349663) ^ ((i + salt) * 83492791);
        var rx = ox + hashU(sd) * CH;
        var rz = oz + hashU(sd ^ 0x9e3779b9) * CH;
        var h = W.heightAt(rx, rz);
        if (!pick(rx, rz, h)) continue;
        var s = scaleMin + hashU(sd ^ 0x85ebca6b) * (scaleMax - scaleMin);
        dummy.position.set(rx, h - 0.16, rz);
        dummy.rotation.set(0, hashU(sd ^ 0xc2b2ae35) * 6.283, 0);
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
      return h > W.WATER_Y + 0.25 && w.g > 0.22 && w.r < 0.5;
    };
    var dry = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.6 && w.g < 0.5;
    };
    var stony = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.4 && w.r > 0.35;
    };

    sow('grass_a', Math.round(320 * (0.35 + cb.grass)), lush, 0.8, 1.6);
    sow('grass_b', Math.round(240 * (0.3 + cb.grass)), lush, 0.7, 1.4);
    sow('fl_orange', Math.round(90 * (0.15 + cb.grass)), lush, 0.8, 1.5);
    sow('fl_yellow', Math.round(80 * (0.15 + cb.grass)), lush, 0.8, 1.5);
    sow('fl_purple', Math.round(70 * (0.12 + cb.grass)), lush, 0.8, 1.5);
    sow('fl_white', Math.round(60 * (0.12 + cb.grass)), lush, 0.8, 1.5);
    sow('bush_dry', Math.round(22 * (1 - cb.grass)), dry, 0.8, 1.7);
    sow('rock_d', Math.round(7 * (0.3 + cb.rock)), stony, 0.8, 2.2);

    /* trees and palms, sparse and deliberate */
    var treeN = Math.max(1, Math.round((3 * cb.grass + 1) * (W.vegScale || 1)));
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
      if (g) {
        g.userData.col = W.addBox(tx, th + sc * 0.30, tz, sc * 0.045 + 0.25, sc * 0.30, sc * 0.045 + 0.25, 0);
        out.push(g);
      }
    }
    /* boulders that you cannot walk through */
    for (var b = 0; b < 2; b++) {
      var bx = ox + rng(ci + b * 3, cj, 2.6) * CH, bz = oz + rng(ci, cj + b * 5, 6.1) * CH;
      var bh = W.heightAt(bx, bz);
      var bw = W.groundWeights(bx, bz, bh);
      if (bh < W.WATER_Y + 1 || bw.r < 0.3) continue;
      var bk = ['rock_a', 'rock_b', 'rock_c'][b % 3];
      if (!MODELS[bk]) continue;
      var bg = place(bk, bx, bh - 0.4, bz, 2.4 + rng(bx, bz, 3) * 5.5, rng(bx, bz, 4) * 6.283, true);
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
    W.addFlat(TOWN.x, TOWN.z, TOWN.R + 14, TOWN.y, 70);

    W.SPAWN = { x: 0, z: TOWN.R + 46 };
    W.SPAWN_YAW = 0;
    W.SHOTS = {
      '1': { x: 0, z: TOWN.R + 70, yaw: 0, pitch: -0.02, h: 2.4 },
      '2': { x: 2, z: 40, yaw: 0.62, pitch: -0.02 },
      '3': { x: 0, z: -(TOWN.R - 3.2), yaw: 0, pitch: -0.20, h: 10.6 },
      '4': { x: 300, z: 400, yaw: 0, pitch: -0.03 },
      '5': { x: 430, z: -228, yaw: 0, pitch: -0.05 },
      '6': { x: -360, z: 306, yaw: 0, pitch: 0.02 },
      '7': { x: -34, z: -6, yaw: 0, pitch: 0.06 },
      '8': { x: 60, z: 300, yaw: 2.2, pitch: -0.16, h: 130, fly: true }
    };

    buildTown();
    buildMosque(-34, -30);
    buildPalace(36, -34);
    buildLibrary(34, 36);
    buildHouses();

    /* lamplight along the streets */
    for (var sl = 0; sl < 10; sl++) {
      var sa = (sl / 10) * Math.PI * 2 + 0.25;
      var sr = 62 + (sl % 3) * 16;
      var sx = Math.cos(sa) * sr, sz = Math.sin(sa) * sr;
      cyl(0.12, 0.16, 3.2, 8, sx, TOWN.y + 1.6, sz, M.dark);
      lamp(sx, TOWN.y + 3.5, sz, 1.35);
    }
    for (var wt = 0; wt < 10; wt++) {
      var wa = (wt / 10) * Math.PI * 2 + 0.9;
      torch(Math.cos(wa) * (TOWN.R - 6.4), TOWN.y + 2.9, Math.sin(wa) * (TOWN.R - 6.4), wa + Math.PI);
    }

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
