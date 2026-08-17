/* Amiratu al-Ulum · the built world
   Town walls and gates, mosque, palace, library, houses, camps, caves,
   fire and lamplight, and everything that grows. */
(function () {
  'use strict';
  var W = window.W;
  var T = THREE;

  var MODELS = {};
  var doors = [];
  W.DOORS = doors;               /* the shot harness reads these */
  var fires = [];
  var lamps = [];
  var winds = [];
  var loader = null;

  /* every flame and lamp registers here; a small pool of real lights
     follows whichever are nearest, so the shaders stay cheap everywhere */
  /* Fire and lamplight.
     A small pool of real lights follows whichever flames are nearest, because a
     scene cannot afford one light per flame. The pool used to snap from source
     to source as you walked, which is what made things flare suddenly. Now a
     light only changes what it serves once it has faded out, and fades back in
     on the new one, so the light in a street changes the way light does. */
  var EMIT = [];
  var POOL = [];
  var POOL_N = 14;
  var MAX_D2 = 9800;

  function initPool() {
    for (var i = 0; i < POOL_N; i++) {
      var l = new T.PointLight(0xffa445, 0, 26, 2);
      l.position.set(0, -9999, 0);
      W.scene.add(l);
      POOL.push({ light: l, src: null, fade: 0 });
    }
  }

  function flicker(e, t) {
    if (e.steady) return 0.94 + 0.06 * Math.sin(t * 2.6 + e.ph);
    /* a candle-like wander: slow body, quick edge, never a strobe */
    return 0.86
      + 0.09 * Math.sin(t * 3.1 + e.ph)
      + 0.05 * Math.sin(t * 7.7 + e.ph * 1.7);
  }

  function driveLights(t, dt) {
    var cp = W.cam.position;
    for (var i = 0; i < EMIT.length; i++) {
      var e = EMIT[i];
      var dx = e.x - cp.x, dy = e.y - cp.y, dz = e.z - cp.z;
      e.d2 = dx * dx + dy * dy + dz * dz;
      e.lit = flicker(e, t);
      e.claimed = false;
    }

    /* keep what each light already serves, if it is still worth serving */
    for (var p = 0; p < POOL_N; p++) {
      var slot = POOL[p];
      if (slot.src && slot.src.d2 < MAX_D2 * 1.6) slot.src.claimed = true;
      else slot.leaving = true;
    }

    /* find the nearest unclaimed emitters for any free slots */
    for (var p2 = 0; p2 < POOL_N; p2++) {
      var s2 = POOL[p2];
      if (s2.src && !s2.leaving) continue;
      if (s2.fade > 0.02) continue;               /* still fading out; wait */
      var best = null;
      for (var k = 0; k < EMIT.length; k++) {
        var e2 = EMIT[k];
        if (e2.claimed || e2.d2 > MAX_D2) continue;
        if (!best || e2.d2 < best.d2) best = e2;
      }
      if (best) { best.claimed = true; s2.src = best; s2.leaving = false; }
      else if (s2.leaving) { s2.src = null; s2.leaving = false; }
    }

    for (var p3 = 0; p3 < POOL_N; p3++) {
      var sl = POOL[p3];
      var want = (sl.src && !sl.leaving) ? 1 : 0;
      sl.fade += (want - sl.fade) * Math.min(1, dt * 2.4);
      var L = sl.light;
      if (!sl.src || sl.fade < 0.01) { L.intensity = 0; continue; }
      var src = sl.src;
      L.color.setHex(src.col);
      L.distance = src.reach;
      L.position.set(src.x, src.y, src.z);
      /* dim with distance as well, so nothing pops as it enters range */
      var range = 1 - W.sstep(MAX_D2 * 0.55, MAX_D2, src.d2);
      L.intensity = Math.min(2.7, src.base * src.lit * sl.fade * range);
    }
  }

  /* ------------------------------------------------------------ helpers */
  /* a real photographed surface: colour, relief and shine */
  function surf(base, color, opts) {
    opts = opts || {};
    var m = new T.MeshStandardMaterial({
      color: color || 0xffffff,
      roughness: opts.rough === undefined ? 1 : opts.rough,
      metalness: 0
    });
    m.map = W.tex('assets/' + base + '_d.jpg', true, true);
    m.normalMap = W.tex('assets/' + base + '_n.jpg', false, true);
    m.normalScale = new T.Vector2(opts.nrm || 1.0, opts.nrm || 1.0);
    if (opts.rmap !== false) m.roughnessMap = W.tex('assets/' + base + '_r.jpg', false, true);
    return m;
  }
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
    M.brick = surf('t_adobe', 0xd9b489, { nrm: 1.2 });
    M.brick2 = surf('t_adobe', 0xc19a74, { nrm: 1.2 });
    M.stone = surf('t_ashlar', 0xe6cda4, { nrm: 1.0 });
    M.stone2 = surf('t_ashlar', 0xd5bb92, { nrm: 1.0 });
    M.marble = surf('t_marble', 0xf3ece6, { nrm: 0.5, rough: 0.42 });
    M.cloth = mat('assets/cloth.jpg', 0xbba98e, 1, [1, 1]);
    M.wood = new T.MeshStandardMaterial({ map: W.tex('assets/t_wood_d.jpg', true, true),
                                          color: 0x9a7a55, roughness: 0.9 });
    M.iron = new T.MeshStandardMaterial({ color: 0x2e2a26, roughness: 0.72, metalness: 0.35 });
    /* the painted door of the reference courtyard: honey-gold arched panels */
    M.doorPaint = new T.MeshStandardMaterial({ map: W.tex('assets/t_door_d.jpg', true), roughness: 0.78 });
    M.dark = new T.MeshStandardMaterial({ color: 0x241a12, roughness: 1 });
    M.metal = new T.MeshStandardMaterial({ color: 0x2a2118, roughness: 0.45, metalness: 0.7 });
    M.gold = new T.MeshStandardMaterial({ color: 0xc9a24a, roughness: 0.3, metalness: 0.9 });
    M.win = new T.MeshBasicMaterial({ color: 0xffc271, toneMapped: false });
    M.winOff = new T.MeshBasicMaterial({ color: 0x0a0b16 });
    M.floor = surf('t_floor', 0xb9a184, { nrm: 0.8 });
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

  /* ---------------------------------------------------------------- fire
     A real flame is not one picture. It is a broad body, a brighter middle and
     a small white core, each moving at its own pace, with embers torn off the
     top and a pool of light on the ground beneath. Built here from three
     billboards on one sheet, a handful of embers, and a light that breathes
     with them. */
  var flameSheets = [];
  var emberTex = null, poolTex = null;
  var FRAMES = 16;

  function initFire() {
    for (var i = 0; i < 4; i++) {
      var t = W.tex('assets/flame.png', true);
      t.repeat.set(1, 1 / FRAMES);
      flameSheets.push(t);
    }
    emberTex = W.tex('assets/ember.png', true);
    poolTex = W.tex('assets/firepool.png', true);
  }

  function flamePlane(tex, w, h, col, op) {
    return new T.Mesh(new T.PlaneGeometry(w, h),
      new T.MeshBasicMaterial({ map: tex, color: col, transparent: true,
        blending: T.AdditiveBlending, depthWrite: false, toneMapped: false, opacity: op }));
  }

  function fire(x, y, z, scale, power) {
    scale = scale || 1;
    power = power === undefined ? 1 : power;
    var g = new T.Group();
    g.position.set(x, y, z);
    W.scene.add(g);

    /* three layers of the same sheet, each on its own frame and its own drift */
    var layers = [];
    var specs = [
      { w: 1.15, h: 1.55, col: 0xff7a1e, op: 0.62, sp: 11 },
      { w: 0.86, h: 1.24, col: 0xffab3e, op: 0.72, sp: 15 },
      { w: 0.55, h: 0.86, col: 0xfff0c8, op: 0.85, sp: 19 }
    ];
    for (var i = 0; i < specs.length; i++) {
      var sp = specs[i];
      var tex = flameSheets[i].clone();
      tex.needsUpdate = true;
      tex.repeat.set(1, 1 / FRAMES);
      var m = flamePlane(tex, sp.w * scale, sp.h * scale, sp.col, sp.op);
      m.position.y = sp.h * scale * 0.5;
      g.add(m);
      layers.push({ mesh: m, tex: tex, sp: sp.sp, off: i * 5 });
    }

    /* the pool of light it throws on the ground */
    var pool = new T.Mesh(new T.PlaneGeometry(5.2 * scale, 5.2 * scale),
      new T.MeshBasicMaterial({ map: poolTex, color: 0xff9a48, transparent: true,
        blending: T.AdditiveBlending, depthWrite: false, toneMapped: false, opacity: 0.34 }));
    pool.rotation.x = -Math.PI / 2;
    pool.position.y = -y + W.heightAt(x, z) + 0.06;
    g.add(pool);

    /* embers, rising and dying */
    var EN = 7;
    var emberGeo = new T.PlaneGeometry(0.075 * scale, 0.075 * scale);
    var emberMat = new T.MeshBasicMaterial({ map: emberTex, color: 0xffc070, transparent: true,
      blending: T.AdditiveBlending, depthWrite: false, toneMapped: false });
    var embers = new T.InstancedMesh(emberGeo, emberMat, EN);
    embers.frustumCulled = false;
    g.add(embers);
    var eState = [];
    for (var e = 0; e < EN; e++) {
      eState.push({ t: Math.random(), sp: 0.5 + Math.random() * 0.7,
                    dx: (Math.random() - 0.5) * 0.5, dz: (Math.random() - 0.5) * 0.5 });
    }

    var f = { g: g, layers: layers, pool: pool, embers: embers, eState: eState,
              base: 2.9 * power, reach: 30 * Math.sqrt(power),
              x: x, y: y + 0.5 * scale, z: z, col: 0xff9a45,
              ph: Math.random() * 10, sc: scale, lit: 1, d2: 0 };
    fires.push(f);
    EMIT.push(f);
    return f;
  }

  var eDummy = new T.Object3D();

  function tickFires(t, dt, cp) {
    for (var i = 0; i < fires.length; i++) {
      var f = fires[i];
      if (f.d2 > 68000) { f.g.visible = false; continue; }
      f.g.visible = true;

      /* each layer runs the sheet at its own speed, so the flame never loops
         visibly and the core dances faster than the body */
      for (var L = 0; L < f.layers.length; L++) {
        var ly = f.layers[L];
        var fr = Math.floor((t * ly.sp + ly.off) % FRAMES);
        ly.tex.offset.y = 1 - (fr + 1) / FRAMES;
        ly.mesh.lookAt(cp.x, ly.mesh.getWorldPosition(new T.Vector3()).y, cp.z);
        var s = 0.93 + 0.14 * Math.sin(t * (5 + L * 2) + f.ph + L);
        ly.mesh.scale.set(s, 0.92 + 0.16 * f.lit, 1);
      }

      f.pool.material.opacity = 0.24 + 0.18 * f.lit;
      f.pool.scale.setScalar(0.94 + 0.1 * f.lit);

      /* embers drift up, fade, and start again */
      if (f.d2 < 9000) {
        f.embers.visible = true;
        for (var e = 0; e < f.eState.length; e++) {
          var st = f.eState[e];
          st.t += dt * st.sp * 0.5;
          if (st.t > 1) { st.t -= 1; st.dx = (Math.random() - 0.5) * 0.5; st.dz = (Math.random() - 0.5) * 0.5; }
          var rise = st.t * 2.4 * f.sc;
          eDummy.position.set(st.dx * st.t * f.sc + Math.sin(t * 2 + e) * 0.08 * st.t,
                              0.5 * f.sc + rise,
                              st.dz * st.t * f.sc + Math.cos(t * 1.7 + e) * 0.08 * st.t);
          eDummy.quaternion.copy(W.cam.quaternion);
          var es = (1 - st.t) * (0.7 + 0.6 * Math.sin(t * 9 + e));
          eDummy.scale.setScalar(Math.max(0.001, es));
          eDummy.updateMatrix();
          f.embers.setMatrixAt(e, eDummy.matrix);
        }
        f.embers.instanceMatrix.needsUpdate = true;
      } else {
        f.embers.visible = false;
      }
    }
  }

  /* a hanging lamp: warm pool of light that fades at its reach */
  function lamp(x, y, z, power, model, reach) {
    var g = new T.Mesh(new T.PlaneGeometry(1.5, 1.5),
      new T.MeshBasicMaterial({ map: W.tex('assets/glow.png', true), color: 0xffd08a, transparent: true, blending: T.AdditiveBlending, depthWrite: false, toneMapped: false, opacity: 0.7 }));
    g.position.set(x, y, z);
    W.scene.add(g);
    var e = { g: g, base: (power || 1.5) * 1.9, reach: reach || 26, x: x, y: y, z: z, col: 0xffb367,
              ph: Math.random() * 9, steady: 1, lit: 1 };
    lamps.push(e);
    EMIT.push(e);
    if (model !== false) place('lantern', x, y - 0.34, z, 0.62, Math.random() * 3);
    return e;
  }

  /* a torch: the iron bracket is a real model, the flame sits in its head */
  function torch(x, y, z, rot) {
    if (MODELS.p_torch) {
      placeBuilt('p_torch', x, y, z, (rot || 0) + Math.PI, 1.0);
      fire(x - Math.sin(rot || 0) * 0.44, y + 1.02, z - Math.cos(rot || 0) * 0.44, 0.42, 1.25);
    } else {
      fire(x, y + 0.5, z, 0.42, 1.25);
    }
  }

  function torchPost(x, y, z) {
    if (MODELS.p_torchpost) {
      placeBuilt('p_torchpost', x, y, z, Math.random() * 6.283, 1.0);
      fire(x, y + 2.62, z, 0.50, 1.45);
    } else {
      fire(x, y + 2.4, z, 0.50, 1.45);
    }
  }

  /* -------------------------------------------------------------- doors */
  /* The leaf is cut to the shape of the opening. A rectangle in a round-headed
     doorway leaves two bright crescents of night showing through the top
     corners, which is what gave the doors away. */
  var leafGeos = {};
  function leafGeometry(w, h) {
    var key = w.toFixed(2) + 'x' + h.toFixed(2);
    if (leafGeos[key]) return leafGeos[key];
    var r = w / 2, straight = Math.max(0.2, h - r);
    var sh = new T.Shape();
    sh.moveTo(0, 0);
    sh.lineTo(w, 0);
    sh.lineTo(w, straight);
    sh.absarc(r, straight, r, 0, Math.PI, false);
    sh.lineTo(0, 0);
    var g = new T.ExtrudeGeometry(sh, { depth: 0.12, bevelEnabled: false, curveSegments: 10 });
    g.translate(0, 0, -0.06);
    leafGeos[key] = g;
    return g;
  }

  function door(x, y, z, w, h, rot, m) {
    var pivot = new T.Group();
    pivot.position.set(x, y, z);
    pivot.rotation.y = rot;
    /* about half the doors are the painted kind, chosen by where they stand
       so the choice never flickers between visits */
    var painted = false;
    var mat = m;
    if (!mat) {
      if (M.doorPaint && hashU(((x * 73.7 + z * 131.3) * 1000) | 0) > 0.965) {
        painted = true;
        mat = M.doorPaint.clone();
        mat.map = M.doorPaint.map.clone();
        mat.map.repeat.set(1 / w, 1 / h);
        mat.map.needsUpdate = true;
      } else {
        mat = M.wood;
      }
    }
    var leaf = new T.Mesh(leafGeometry(w, h), mat);
    pivot.add(leaf);
    if (!painted) {
      /* the planks and the ledger that hold a board door together */
      for (var pl = 1; pl < 4; pl++) {
        var rib = new T.Mesh(new T.BoxGeometry(0.045, h * 0.94, 0.03), M.wood);
        rib.position.set(w * pl / 4, h * 0.47, 0.075);
        pivot.add(rib);
      }
      var band = new T.Mesh(new T.BoxGeometry(w * 0.92, 0.09, 0.035), M.iron || M.wood);
      band.position.set(w / 2, h * 0.28, 0.08);
      pivot.add(band);
    }
    var knob = new T.Mesh(new T.SphereGeometry(0.06, 8, 6), M.gold);
    knob.position.set(w - 0.18, h * 0.5, 0.1);
    pivot.add(knob);
    W.scene.add(pivot);
    /* rotation.y maps the leaf's +x to world (cos, -sin) -- the collider
       must live on the same side, or turned doors hang beside their wall */
    var cx = x + Math.cos(rot) * w / 2, cz = z - Math.sin(rot) * w / 2;
    var col = W.addBox(cx, y + h / 2, cz, w / 2, h / 2, 0.1, rot);
    var d = { pivot: pivot, col: col, open: false, ang: 0, x: x, z: z,
              hw: w / 2, y0: col.y0, y1: col.y1 };
    doors.push(d);
    return d;
  }

  /* Some models arrive with geometry but no surface. We paint them ourselves,
     projecting a photographed wall from three directions and blending by normal,
     so no unwrapping is needed and the stone never smears. */
  function triplanar(base, color, scale, rough) {
    var m = new T.MeshStandardMaterial({ color: color, roughness: rough === undefined ? 0.97 : rough, metalness: 0 });
    var mapT = W.tex('assets/' + base + '_d.jpg', true, true);
    m.map = mapT;
    m.onBeforeCompile = function (sh) {
      sh.uniforms.tTri = { value: mapT };
      sh.uniforms.uScale = { value: scale || 0.34 };
      sh.vertexShader = 'varying vec3 vTriP;\nvarying vec3 vTriN;\n' + sh.vertexShader.replace(
        '#include <begin_vertex>',
        ['#include <begin_vertex>',
         'vTriP = (modelMatrix * vec4(transformed,1.0)).xyz;',
         'vTriN = normalize(mat3(modelMatrix) * objectNormal);'].join('\n')
      );
      sh.fragmentShader = ['uniform sampler2D tTri;', 'uniform float uScale;',
        'varying vec3 vTriP;', 'varying vec3 vTriN;', ''].join('\n') + sh.fragmentShader;
      sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', [
        'vec3 bw = pow(abs(vTriN), vec3(4.0));',
        'bw /= max(0.0001, (bw.x + bw.y + bw.z));',
        'vec3 tx = texture2D(tTri, vTriP.zy * uScale).rgb;',
        'vec3 ty = texture2D(tTri, vTriP.xz * uScale).rgb;',
        'vec3 tz = texture2D(tTri, vTriP.xy * uScale).rgb;',
        'vec3 tri = tx * bw.x + ty * bw.y + tz * bw.z;',
        'vec3 mx = texture2D(tTri, vTriP.zy * uScale * 0.19).rgb;',
        'vec3 my = texture2D(tTri, vTriP.xz * uScale * 0.19).rgb;',
        'vec3 mz = texture2D(tTri, vTriP.xy * uScale * 0.19).rgb;',
        'vec3 mac = mx * bw.x + my * bw.y + mz * bw.z;',
        'tri *= (0.62 + 0.78 * mac.r);',
        'diffuseColor.rgb *= tri;'
      ].join('\n'));
    };
    m.customProgramCacheKey = function () { return 'tri' + base + (scale || 0.34); };
    return m;
  }
  W.triplanar = triplanar;

  /* Buildings made in Blender arrive with a collision file listing every solid
     box in them. We use those directly, so parapets lift you, stairs step true,
     and nothing has an invisible margin. */
  var COLJSON = {}, SPOTJSON = {};
  function loadCollision(name) {
    return fetch('assets/models/' + name + '.col.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j) return;
        COLJSON[name] = j.boxes;
        if (j.spots) SPOTJSON[name] = j.spots;
      })
      .catch(function () {});
  }
  function placeBuilt(name, x, y, z, rot, scale) {
    var g = place(name, x, y, z, null, rot, false, 'raw', scale);
    if (!g) return null;
    var boxes = COLJSON[name];
    if (!boxes) return g;
    var c = Math.cos(rot || 0), s2 = Math.sin(rot || 0);
    var k = scale || 1;
    for (var i = 0; i < boxes.length; i++) {
      var b = boxes[i];
      var bx = b.c[0] * k, by = b.c[1] * k, bz = b.c[2] * k;
      /* rotation.y carries local (x,z) to world (x c + z s, -x s + z c) */
      W.addBox(x + bx * c + bz * s2, y + by, z - bx * s2 + bz * c,
               b.h[0] * k, b.h[1] * k, b.h[2] * k, rot || 0);
    }
    return g;
  }

  /* ------------------------------------------------------------- models */
  /* size is the wanted height, unless axis is 'x' (flat things like rugs) */
  function place(key, x, y, z, size, rot, solid, axis, rawScale) {
    var src = MODELS[key];
    if (!src) return null;
    var o = src.clone(true);
    var bb = new T.Box3().setFromObject(o);
    var sz = new T.Vector3(); bb.getSize(sz);
    var s;
    if (axis === 'raw') {
      s = rawScale || 1;
    } else {
      var ref = (axis === 'x') ? Math.max(sz.x, sz.z) : sz.y;
      s = size / Math.max(0.0001, ref);
    }
    o.scale.setScalar(s);
    bb.setFromObject(o);
    if (axis === 'raw') o.position.set(0, 0, 0);
    else o.position.set(-(bb.min.x + bb.max.x) / 2, -bb.min.y, -(bb.min.z + bb.max.z) / 2);
    var g = new T.Group();
    g.add(o);
    g.position.set(x, y - (axis === 'raw' ? 0.02 : 0.14), z);
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
        W.MODELS_IN = true;      /* fixed-viewpoint capture waits for this */
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
            o.castShadow = true; o.receiveShadow = true;
            if (o.material) {
              o.material.envMapIntensity = 0.35;
              if (o.material.map) o.material.map.anisotropy = 4;
            }
          }
        });
        if (name.indexOf('p_') === 0) {
          g.scene.traverse(function (o) {
            if (o.isMesh && o.material) {
              o.castShadow = false;
              /* the baked occlusion now carries most of the shading, so the
                 base tone sits higher than it did when surfaces were flat */
              o.material.color.multiplyScalar(0.95);
              o.material.roughness = 1;
              o.material.metalness = 0;
              if (o.geometry.attributes.color_1) o.geometry.deleteAttribute('color_1');
            }
          });
        } else if (name.indexOf('bh') === 0) {
          g.scene.traverse(function (o) {
            if (o.isMesh && o.material) {
              o.material.color.setHex(0xe6c6a0);      /* sun-dried mud · occlusion darkens it back down */
              o.material.roughness = 1;
              o.material.metalness = 0;
              if (o.geometry.attributes.color_1) o.geometry.deleteAttribute('color_1');
              if (o.material.map) { o.material.map.anisotropy = 8; }
            }
          });
        } else if (name.indexOf('ah') === 0 && name.length === 3) {
          if (!M.wallTri) M.wallTri = triplanar('t_adobe', 0xd9b78c, 0.34);
          g.scene.traverse(function (o) { if (o.isMesh) o.material = M.wallTri; });
        } else if (name === 'mosque_orn') {
          if (!M.mosqueTri) M.mosqueTri = triplanar('t_ashlar', 0xe7d0a8, 0.20, 0.9);
          g.scene.traverse(function (o) { if (o.isMesh) o.material = M.mosqueTri; });
        } else if (name.indexOf('house_') === 0 || name === 'kasbah') {
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

  /* The clutter of a lived-in town. Each building carries a list of flat places
     where things may stand, and every house gets a different set. */
  var PROPS_ROOF = ['p_carpet', 'p_cushions', 'p_table', 'p_stool', 'p_chest', 'p_books',
                    'p_scrolls', 'p_inkset', 'p_bowl', 'p_bread', 'p_pot', 'p_plantpot',
                    'p_broom', 'p_basket', 'p_waterjug', 'p_oillamp', 'p_jars',
                    'p_ropecoil', 'p_firewood', 'p_crates', 'p_sacks', 'p_barrel', 'p_ladder'];
  var PROPS_ARMS = ['p_spears', 'p_swordrack', 'p_bowarrows'];
  var PROPS_ROOM = ['p_carpet', 'p_cushions', 'p_table', 'p_stool', 'p_chest', 'p_books',
                    'p_scrolls', 'p_inkset', 'p_bowl', 'p_pot', 'p_waterjug', 'p_basket'];
  var PROPS_STREET = ['p_barrels', 'p_crates', 'p_jars', 'p_sacks', 'p_cart', 'p_bench',
                      'p_stall', 'p_awning', 'p_stones', 'p_ropecoil', 'p_firewood', 'p_pergola',
                      'p_plantpot', 'p_basket', 'p_waterjug'];
  var ALL_PROPS = PROPS_ROOF.concat(PROPS_ARMS, PROPS_STREET,
                                    ['p_brazier', 'p_well', 'p_torch', 'p_torchpost']);

  /* Props are drawn out to a distance that matches their size. Anything that
     shows in a silhouette from across the square keeps its range; a bowl or an
     inkpot is invisible at twenty paces and is not worth a draw call. */
  var BIG_PROP = {
    p_carpet: 1, p_table: 1, p_chest: 1, p_awning: 1, p_stall: 1, p_cart: 1,
    p_bench: 1, p_barrel: 1, p_barrels: 1, p_crates: 1, p_sacks: 1, p_jars: 1,
    p_plantpot: 1, p_spears: 1, p_swordrack: 1, p_brazier: 1, p_well: 1,
    p_torch: 1, p_torchpost: 1, p_firewood: 1, p_basket: 1, p_pot: 1,
    p_stones: 1, p_pergola: 1, p_ladder: 1
  };
  var SMALL = [];

  function propOn(list, seed, x, y, z, rot, scale) {
    var key = list[Math.floor(hashU(seed) * list.length) % list.length];
    if (!MODELS[key]) return null;
    var g = placeBuilt(key, x, y, z, rot, scale || 1);
    if (g) { g.userData.far = BIG_PROP[key] ? 19600 : 2500; SMALL.push(g); }
    return g;
  }

  /* fill one building's flat places with a different set each time */
  function dressBuilding(name, bx, by, bz, brot, scale, seedBase) {
    var spots = SPOTJSON[name];
    if (!spots) return;
    var c = Math.cos(brot), s2 = Math.sin(brot);
    for (var i = 0; i < spots.length; i++) {
      var sp = spots[i];
      if (sp.k === 'door') {
        /* a leaf on its hinge, turned to the face it was exported on */
        var hx = (sp.c[0] * scale) * c + (sp.c[2] * scale) * s2;
        var hz = -(sp.c[0] * scale) * s2 + (sp.c[2] * scale) * c;
        var face = brot + ((sp.f || 0) * Math.PI / 180);
        door(bx + hx, by + sp.c[1] * scale, bz + hz,
             sp.r[0] * scale * 0.97, sp.r[1] * scale * 0.97, face);
        continue;
      }
      var n = sp.k === 'room' ? 3 : (sp.k === 'balcony' ? 2 : 4);
      for (var j = 0; j < n; j++) {
        var sd = (seedBase * 2654435761) ^ ((i * 40503 + j * 7919) | 0);
        var u = (hashU(sd) - 0.5) * 2, v = (hashU(sd ^ 0x51ab) - 0.5) * 2;
        /* the middle of a court belongs to its fountain */
        if (sp.k === 'court' && Math.abs(u * sp.r[0]) < 4.6 && Math.abs(v * sp.r[1]) < 4.6) continue;
        var lx = (sp.c[0] + u * sp.r[0]) * scale;
        var lz = (sp.c[2] + v * sp.r[1]) * scale;
        var ly = sp.c[1] * scale;
        var wx = bx + lx * c + lz * s2;
        var wz = bz - lx * s2 + lz * c;
        var list = sp.k === 'room' ? PROPS_ROOM
                 : (hashU(sd ^ 0x99) > 0.86 ? PROPS_ARMS : PROPS_ROOF);
        propOn(list, sd, wx, by + ly, wz, hashU(sd ^ 0x77) * 6.283, 1);
        /* a lamp burning on some terraces */
        if (sp.k !== 'room' && j === 0 && hashU(sd ^ 0x1234) > 0.55) {
          lamp(wx, by + ly + 0.9, wz, 0.85);
        }
        /* Rooms are lit from within, so a window reads as a lit window and not
           a black hole punched in the wall. Most houses, not all -- some
           people have gone to bed. */
        if (sp.k === 'room' && j === 0 && hashU(sd ^ 0x2b1d) > 0.28) {
          var rx = bx + (sp.c[0] * scale) * c - (sp.c[2] * scale) * s2;
          var rz = bz + (sp.c[0] * scale) * s2 + (sp.c[2] * scale) * c;
          /* short reach on purpose · point lights are not stopped by walls, so
             a room lamp with a long reach lights the street outside through
             the wall, and walking past a house made the night flare */
          lamp(rx, by + ly + 1.35, rz, 0.5, false, 6.5);
        }
      }
    }
  }

  /* A market stands in every open place: stalls under awnings around the rim,
     the goods stacked behind them, a brazier for the cold. Without this the
     squares read as empty yards, which is the one thing a town square is not. */
  function dressSquares() {
    var GOODS = ['p_jars', 'p_crates', 'p_sacks', 'p_barrels', 'p_basket',
                 'p_pot', 'p_waterjug', 'p_ropecoil', 'p_firewood', 'p_stones'];
    for (var q = 0; q < SQUARES.length; q++) {
      var sq = SQUARES[q];
      var stalls = 5 + Math.floor(hashU((q * 7717) | 0) * 4);
      for (var i = 0; i < stalls; i++) {
        var sd = (q * 92821 + i * 51203) | 0;
        var a = (i / stalls) * 6.283 + hashU(sd) * 0.6;
        var rr = sq.r * (0.72 + hashU(sd ^ 0x3) * 0.34);
        var sx = sq.x + Math.cos(a) * rr, sz = sq.z + Math.sin(a) * rr;
        if (W.roadAt && W.roadAt(sx, sz) > 0.55) continue;
        var face = Math.atan2(sq.x - sx, sq.z - sz);      /* face the square */
        var y = W.heightAt(sx, sz);
        placeBuilt(hashU(sd ^ 0x9) > 0.45 ? 'p_stall' : 'p_awning', sx, y, sz, face, 1);
        /* the goods behind the stall, and one thing set out in front */
        for (var k = 0; k < 3; k++) {
          var gd = (sd ^ (k * 7919)) | 0;
          var back = 1.9 + hashU(gd) * 1.5;
          var side = (hashU(gd ^ 0x5) - 0.5) * 3.4;
          propOn(GOODS, gd,
                 sx - Math.sin(face) * (k === 2 ? -1.7 : back) + Math.cos(face) * side,
                 y,
                 sz - Math.cos(face) * (k === 2 ? -1.7 : back) - Math.sin(face) * side,
                 hashU(gd ^ 0xb) * 6.283, 1);
        }
      }
      /* something burning at the middle of the square */
      var bx = sq.x + (hashU((q * 331) | 0) - 0.5) * 6;
      var bz = sq.z + (hashU((q * 733) | 0) - 0.5) * 6;
      var by = W.heightAt(bx, bz);
      if (MODELS.p_brazier) placeBuilt('p_brazier', bx, by, bz, hashU(q) * 6.283, 1);
      fire(bx, by + 0.62, bz, 0.66, 1.15);
      /* and a cart left standing */
      if (hashU((q * 1471) | 0) > 0.35) {
        var cx2 = sq.x + Math.cos(q * 2.1) * sq.r * 0.55;
        var cz2 = sq.z + Math.sin(q * 2.1) * sq.r * 0.55;
        propOn(['p_cart', 'p_bench'], (q * 5501) | 0, cx2, W.heightAt(cx2, cz2), cz2,
               hashU((q * 17) | 0) * 6.283, 1);
      }
    }
  }

  /* ---------------------------------------------------------- the town */
  var TOWN = { x: 0, z: 0, y: 0, R: 118 };

  /* A square citadel, assembled from Blender-made pieces so the walls carry the
     same eroded stone as the houses. Every piece brings its own collision. */
  var TOWNSQ = 132;
  var WALL_KIT = ['w_seg', 'w_tower', 'w_tower_big', 'w_gate', 'm_mosque'];
  var SEG_LEN = 12.0, GATE_HALF = 6.5;

  function buildTown() {
    /* the walls need their models · assembled once those have arrived */
  }

  function buildCitadel() {
    var Y = TOWN.y, S = TOWNSQ;
    if (!MODELS.w_seg) { W.diag('wall pieces missing'); return; }

    /* four runs; yaw turns each piece to face outward */
    var runs = [
      { x0: -S, z0: S, x1: S, z1: S, yaw: 0 },              /* south, holds the gate */
      { x0: S, z0: -S, x1: -S, z1: -S, yaw: Math.PI },      /* north */
      { x0: -S, z0: -S, x1: -S, z1: S, yaw: -Math.PI / 2 },  /* west */
      { x0: S, z0: S, x1: S, z1: -S, yaw: Math.PI / 2 }      /* east */
    ];

    runs.forEach(function (r, ri) {
      var dx = r.x1 - r.x0, dz = r.z1 - r.z0;
      var len = Math.hypot(dx, dz);
      var n = Math.round(len / SEG_LEN);
      var ux = dx / len, uz = dz / len;
      for (var i = 0; i < n; i++) {
        var t = (i + 0.5) / n;
        var cx = r.x0 + dx * t, cz = r.z0 + dz * t;
        if (ri === 0 && Math.abs(cx) < GATE_HALF + 8.5) continue;   /* leave the gateway */
        placeBuilt('w_seg', cx, Y, cz, r.yaw, 1.0);
      }
    });

    /* towers: bigger at the corners, regular ones along each run */
    [[-S, -S], [S, -S], [-S, S], [S, S]].forEach(function (c) {
      placeBuilt('w_tower_big', c[0], Y, c[1], 0, 1.0);
    });
    for (var k = 1; k <= 4; k++) {
      var f = k / 5;
      var at = -S + S * 2 * f;
      placeBuilt('w_tower', at, Y, -S, 0, 1.0);
      placeBuilt('w_tower', -S, Y, at, 0, 1.0);
      placeBuilt('w_tower', S, Y, at, 0, 1.0);
      if (Math.abs(f - 0.5) > 0.18) placeBuilt('w_tower', at, Y, S, 0, 1.0);
    }

    /* the gatehouse */
    placeBuilt('w_gate', 0, Y, S, 0, 1.0);
    torch(-GATE_HALF - 1.0, Y + 3.8, S + 7.2, 0);
    torch(GATE_HALF + 1.0, Y + 3.8, S + 7.2, 0);
    torch(-GATE_HALF - 1.0, Y + 3.8, S - 7.2, 0);
    torch(GATE_HALF + 1.0, Y + 3.8, S - 7.2, 0);

    /* Stairs against the inner face of the wall. They start out along the wall,
       away from the gate, and climb toward it, topping out on the rampart walk
       just short of the gatehouse.

       The two numbers below are measured off the wall pieces themselves, not
       guessed: the walk surface stands RAMPART_Y above the town floor, and its
       inner edge is WALK_IN in from the wall line. Getting either wrong leaves
       the stair hanging in the air short of the wall, which is exactly what it
       used to do -- two and a half metres shy in both directions. */
    var RAMPART_Y = 15.95;
    var WALK_IN = 3.2;
    /* One solid wedge of masonry carries each flight -- a single surface, so
       the wall texture runs unbroken down the flank instead of restarting on
       every step the way the old stacked slabs did. Thin treads ride its back
       and carry the walkable colliders. */
    function stairWedge(xFoot, xTop, yBase, hTop, z, deep, m) {
      var len = Math.abs(xTop - xFoot);
      var g = uvScaleBox(new T.BoxGeometry(len, 1, deep), len, hTop, deep);
      g.translate(0, 0.5, 0);                     /* bottom at local y 0 */
      var pa = g.attributes.position;
      var dirRight = xTop > xFoot ? 1 : -1;
      for (var vi = 0; vi < pa.count; vi++) {
        if (pa.getY(vi) > 0.5) {
          var t = (pa.getX(vi) * dirRight + len / 2) / len;   /* 0 at foot */
          pa.setY(vi, Math.max(0.3, hTop * t));
        }
      }
      g.computeVertexNormals();
      /* courses stay horizontal: reproject every face flat from position,
         or the shear drags the masonry into a diagonal weave */
      var uv2 = g.attributes.uv, pp = g.attributes.position;
      var mx = (xFoot + xTop) / 2;
      for (var fi = 0; fi < 6; fi++) {
        for (var vi2 = 0; vi2 < 4; vi2++) {
          var k2 = fi * 4 + vi2;
          var px = pp.getX(k2) + mx, py = pp.getY(k2) + yBase, pz = pp.getZ(k2) + z;
          if (fi < 2) uv2.setXY(k2, pz / TILE, py / TILE);        /* ends   */
          else if (fi < 4) uv2.setXY(k2, px / TILE, pz / TILE);   /* top    */
          else uv2.setXY(k2, px / TILE, py / TILE);               /* flanks */
        }
      }
      uv2.needsUpdate = true;
      var mesh = new T.Mesh(g, m);
      mesh.position.set((xFoot + xTop) / 2, yBase, z);
      W.scene.add(mesh);
      /* coarse side blocking, thirds of rising height */
      for (var k3 = 0; k3 < 3; k3++) {
        var t0 = k3 / 3, t1 = (k3 + 1) / 3;
        var hh = hTop * (t0 + t1) / 2;
        var cx3 = xFoot + (xTop - xFoot) * (t0 + t1) / 2;
        W.addBox(cx3, yBase + hh / 2, z, len / 6, hh / 2, deep / 2, 0);
      }
      return mesh;
    }
    [-1, 1].forEach(function (sgn) {
      var steps = 26, rise = RAMPART_Y / steps, run = 1.5;
      var far = sgn * (GATE_HALF + 16 + steps * run);   /* the foot, away from the gate */
      var deep = 7.2;                                   /* runs back INTO the wall */
      var zIn = S - WALK_IN - deep / 2 + 1.4;           /* so the top tread overlaps the walk */
      var xTop = far - sgn * steps * run;
      stairWedge(far, xTop, Y, RAMPART_Y, zIn, deep, M.stone2);
      for (var i = 0; i < steps; i++) {
        var h = rise * (i + 1);
        var x = far - sgn * i * run;
        box(run + 0.1, 0.34, deep, x, Y + h - 0.17, zIn, M.stone2, 0);
      }
      /* the landing, level with the walk */
      box(4.8, 1.0, deep, far - sgn * steps * run, Y + RAMPART_Y - 0.5, zIn, M.stone2, 0);
    });

    /* Torches along the rampart, bracketed to the parapet and standing over
       the walk. They used to hang in mid air a metre inside the wall and two
       metres below the walk floor. */
    for (var w2 = 0; w2 < 12; w2++) {
      var a2 = w2 / 12;
      var tx = -S + S * 2 * a2;
      torch(tx, Y + RAMPART_Y + 1.15, S - 1.9, 0);
      torch(tx, Y + RAMPART_Y + 1.15, -S + 1.9, Math.PI);
      torch(S - 1.9, Y + RAMPART_Y + 1.15, tx, -Math.PI / 2);
      torch(-S + 1.9, Y + RAMPART_Y + 1.15, tx, Math.PI / 2);
    }

    /* Things stacked against the inside of the wall. A town wall is never a
       clean skirting board -- stone left over from the building of it, cut
       firewood, stores nobody has moved. It is what makes the base read as
       lived in rather than as a wall meeting a floor. */
    var LEAN = ['p_stones', 'p_firewood', 'p_crates', 'p_barrels', 'p_sacks',
                'p_jars', 'p_ropecoil', 'p_basket', 'p_stones', 'p_crates'];
    var IN = S - 8.6;
    for (var side = 0; side < 4; side++) {
      for (var n2 = 0; n2 < 16; n2++) {
        var sd3 = (side * 91967 + n2 * 40597) | 0;
        if (hashU(sd3) < 0.36) continue;                  /* leave gaps */
        var along = -S + 12 + hashU(sd3 ^ 0x5a) * (S * 2 - 24);
        /* the south run carries the gateway and both rampart stairs */
        if (side === 0 && Math.abs(along) < 62) continue;
        var jitter = hashU(sd3 ^ 0xa7) * 2.6;
        var px, pz, face;
        if (side === 0)      { px = along;      pz = IN - jitter;  face = 0; }
        else if (side === 1) { px = along;      pz = -IN + jitter; face = Math.PI; }
        else if (side === 2) { px = IN - jitter; pz = along;       face = -Math.PI / 2; }
        else                 { px = -IN + jitter; pz = along;      face = Math.PI / 2; }
        propOn(LEAN, sd3, px, Y, pz, face + (hashU(sd3 ^ 0xd1) - 0.5) * 0.7, 1);
      }
    }
  }

  /* the friday mosque · dome, minaret, mihrab, lamps */
  function buildMosque(cx, cz) {
    W.MOSQUE_BUILT = [];
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

  /* the housing: real sculpted kasbah houses, with a few of our own that open */
  var BUILT = ['bh21','bh22','bh23','bh24','bh25','bh26','bh27','bh28','bh29','bh30'];
  var HOUSE_SCALE = 1.38;

  function buildHouses() {
    /* nothing is built up front any more · the houses are made in Blender and
       arrive with their own collision, so they are placed once loaded */
  }

  /* Houses laid along streets inside the square, packed the way a desert town
     packs: rows facing the lanes, backs close together. */
  /* HOW THE TOWN GROWS
     Not rows, and not a few lanes drawn by hand. A desert town is built the
     other way round: ways get worn between the places people go, houses are
     packed into whatever ground is left, and the streets are the gaps that
     survive. So here we first grow a network of ways from the gate to the
     mosque, the well and the squares, branch smaller lanes off them until the
     ground is served, then pack houses into every space that is left, letting
     them crowd, share walls and turn to face whatever way runs past them.
     Dead ends and narrow niches appear on their own, because they are what is
     left over, which is exactly how they appear in a real town. */

  var WAYS = [];          /* every segment of every street */

  function way(ax, az, bx, bz, half) {
    WAYS.push({ ax: ax, az: az, bx: bx, bz: bz, half: half });
  }

  /* a way between two places never runs straight · it wanders and settles */
  function wander(ax, az, bx, bz, half, sway, depth, seed) {
    if (depth <= 0) { way(ax, az, bx, bz, half); return; }
    var mx = (ax + bx) / 2, mz = (az + bz) / 2;
    var dx = bx - ax, dz = bz - az;
    var len = Math.hypot(dx, dz);
    var nx = -dz / len, nz = dx / len;
    var push = (hashU(seed) - 0.5) * sway;
    mx += nx * push; mz += nz * push;
    wander(ax, az, mx, mz, half, sway * 0.55, depth - 1, (seed * 1103515245 + 12345) | 0);
    wander(mx, mz, bx, bz, half, sway * 0.55, depth - 1, (seed * 214013 + 2531011) | 0);
  }

  function distToWays(x, z) {
    var best = 1e9, bestSeg = null;
    for (var i = 0; i < WAYS.length; i++) {
      var w = WAYS[i];
      var dx = w.bx - w.ax, dz = w.bz - w.az;
      var l2 = dx * dx + dz * dz;
      var t = l2 > 0 ? Math.max(0, Math.min(1, ((x - w.ax) * dx + (z - w.az) * dz) / l2)) : 0;
      var px = w.ax + dx * t, pz = w.az + dz * t;
      var d = Math.hypot(x - px, z - pz) - w.half;
      if (d < best) { best = d; bestSeg = { px: px, pz: pz }; }
    }
    return { d: best, at: bestSeg };
  }

  var SQUARES = [];       /* the open places · where a market stands */

  function growStreets(S) {
    WAYS.length = 0;
    var gate = [0, S - 12];
    var mosque = [-40, -34];
    var well = [6, 8];
    var plazaA = [58, -58];
    var plazaB = [-64, 52];
    var plazaC = [70, 62];
    SQUARES = [
      { x: well[0], z: well[1], r: 15 },
      { x: plazaA[0], z: plazaA[1], r: 13 },
      { x: plazaB[0], z: plazaB[1], r: 13 },
      { x: plazaC[0], z: plazaC[1], r: 12 },
      { x: 0, z: S - 30, r: 16 },            /* inside the gate */
      { x: mosque[0] + 22, z: mosque[1] + 20, r: 12 }
    ];

    /* the arteries: the ways everyone walks */
    wander(gate[0], gate[1], well[0], well[1], 6.0, 26, 3, 1013);
    wander(well[0], well[1], mosque[0], mosque[1], 5.2, 22, 3, 2027);
    wander(well[0], well[1], plazaA[0], plazaA[1], 4.8, 30, 3, 3041);
    wander(well[0], well[1], plazaB[0], plazaB[1], 4.8, 30, 3, 4057);
    wander(plazaA[0], plazaA[1], plazaC[0], plazaC[1], 4.2, 26, 3, 5077);
    wander(mosque[0], mosque[1], plazaB[0], plazaB[1], 4.2, 24, 3, 6091);
    wander(gate[0], gate[1], plazaA[0], plazaA[1], 4.4, 34, 3, 7103);

    /* lanes branching off, until the ground is served */
    var arteries = WAYS.slice();
    for (var b = 0; b < 26; b++) {
      var sd = (b * 2654435761) | 0;
      var src = arteries[Math.floor(hashU(sd) * arteries.length) % arteries.length];
      var t = 0.2 + hashU(sd ^ 0x11) * 0.6;
      var sx = src.ax + (src.bx - src.ax) * t;
      var sz = src.az + (src.bz - src.az) * t;
      var dx = src.bx - src.ax, dz = src.bz - src.az;
      var len = Math.hypot(dx, dz) || 1;
      var nx = -dz / len, nz = dx / len;
      var side = hashU(sd ^ 0x22) > 0.5 ? 1 : -1;
      var reach = 26 + hashU(sd ^ 0x33) * 54;
      var ex = sx + nx * side * reach + (hashU(sd ^ 0x44) - 0.5) * 30;
      var ez = sz + nz * side * reach + (hashU(sd ^ 0x55) - 0.5) * 30;
      ex = Math.max(-S + 34, Math.min(S - 34, ex));
      ez = Math.max(-S + 34, Math.min(S - 34, ez));
      var half = hashU(sd ^ 0x66) > 0.72 ? 1.5 : (hashU(sd ^ 0x77) > 0.45 ? 2.4 : 3.4);
      wander(sx, sz, ex, ez, half, 18, 2, sd ^ 0x88);
    }
  }

  function buildSculptedHouses() {
    var Y = TOWN.y, S = TOWNSQ, made = 0, idx = 0;
    growStreets(S);

    var placed = [];
    var RAD = 8.4 * HOUSE_SCALE * 0.62;    /* how much ground one house needs */

    function keepOut(x, z) {
      if (Math.hypot(x + 40, z + 34) < 36) return true;   /* the mosque */
      if (Math.hypot(x + 40, z - 3) < 27) return true;    /* its courtyard */
      if (Math.hypot(x - 6, z - 8) < 14) return true;     /* the well square */
      if (Math.abs(x) > S - 30 || Math.abs(z) > S - 30) return true;
      return false;
    }

    /* Scatter candidates over the whole town, keep the ones that fit. The
       leftovers between them become the alleys and dead ends. */
    var STEP = 5.0;
    for (var gz = -S + 34; gz < S - 34; gz += STEP) {
      for (var gx = -S + 34; gx < S - 34; gx += STEP) {
        var sd = ((gx * 73856093) ^ (gz * 19349663)) | 0;
        var x = gx + (hashU(sd) - 0.5) * STEP * 1.6;
        var z = gz + (hashU(sd ^ 0x9e3) - 0.5) * STEP * 1.6;
        if (keepOut(x, z)) continue;

        var near = distToWays(x, z);
        /* it must stand clear of the roadway, but close enough to be served */
        if (near.d < RAD * 0.72) continue;
        if (near.d > 26) continue;

        var ok = true;
        for (var i = 0; i < placed.length; i++) {
          var pl = placed[i];
          var need = (hashU(sd ^ (i * 7919)) > 0.80) ? RAD * 1.42 : RAD * 1.86;
          if (Math.hypot(x - pl[0], z - pl[1]) < need) { ok = false; break; }
        }
        if (!ok) continue;

        var key = BUILT[idx % BUILT.length];
        idx++;
        if (!MODELS[key]) continue;
        /* turn to face whatever way runs nearest, but never squarely */
        var facing = Math.atan2(near.at.px - x, near.at.pz - z) + (hashU(sd ^ 0xabc) - 0.5) * 0.5;
        var g = placeBuilt(key, x, Y, z, facing, HOUSE_SCALE);
        if (!g) continue;
        placed.push([x, z]);
        made++;
        dressBuilding(key, x, Y, z, facing, HOUSE_SCALE, idx * 31 + 7);

        var fx = Math.sin(facing), fz = Math.cos(facing);
        if (idx % 4 === 0) torch(x + fx * 7.2, Y + 2.9, z + fz * 7.2, facing);
        if (idx % 6 === 0) lamp(x + fx * 6.4, Y + 3.3, z + fz * 6.4, 1.0, false);
        for (var q = 0; q < 2; q++) {
          var sd2 = (idx * 7919 + q * 104729) | 0;
          if (hashU(sd2) < 0.52) continue;
          propOn(PROPS_STREET, sd2,
                 x + fx * (8.2 + hashU(sd2 ^ 3) * 2.4) + fz * (hashU(sd2 ^ 7) - 0.5) * 7,
                 Y,
                 z + fz * (8.2 + hashU(sd2 ^ 3) * 2.4) - fx * (hashU(sd2 ^ 7) - 0.5) * 7,
                 hashU(sd2 ^ 9) * 6.283, 1);
        }
      }
    }

    /* lamps set where the ways meet, not on a grid */
    for (var L = 0; L < WAYS.length; L += 3) {
      var w2 = WAYS[L];
      if (w2.half < 3) continue;
      var lx = (w2.ax + w2.bx) / 2, lz = (w2.az + w2.bz) / 2;
      if (keepOut(lx, lz)) continue;
      if (hashU((L * 2654435761) | 0) > 0.45) {
        torchPost(lx, TOWN.y, lz);
      } else {
        cyl(0.11, 0.15, 3.4, lx, TOWN.y + 1.7, lz, M.stone2);
        cyl(0.22, 0.16, 0.24, lx, TOWN.y + 3.5, lz, M.metal, false);
        lamp(lx, TOWN.y + 3.9, lz, 1.25);
      }
    }

    W.WAYS = WAYS;
    if (!made) W.diag('no houses were placed');
  }

  /* a desert camp: open tents around a fire */
  function buildCamp(cx, cz, n) {
    var Y = Math.max(W.heightAt(cx, cz), W.WATER_Y + 2.2);
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
    var Y = Math.max(W.heightAt(cx, cz), W.WATER_Y + 2.2);
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

  /* Places stamped on the hand-drawn map stand up in the world. */
  function buildMapSites() {
    var MP = W.MAPW;
    if (!MP || !MP.sites) return;
    MP.sites.forEach(function (st, si) {
      var x = st.x, z = st.z;
      var y = W.heightAt(x, z);
      var sd = (si * 48611 + 977) | 0;
      if (st.k === 'camp') { buildCamp(x, z, 3); }
      else if (st.k === 'cave') { buildCave(x, z); }
      else if (st.k === 'bustan') { buildBustan(x, z); }
      else if (st.k === 'village') {
        for (var i = 0; i < 6; i++) {
          var a = i / 6 * 6.283 + hashU((sd ^ i) | 0);
          var r = 14 + hashU((sd ^ (i * 31)) | 0) * 16;
          var hx = x + Math.cos(a) * r, hz = z + Math.sin(a) * r;
          var key = 'bh' + (21 + ((si * 7 + i) % 10));
          if (MODELS[key]) {
            var rot = hashU((sd ^ (i * 91)) | 0) * 6.283;
            placeBuilt(key, hx, W.heightAt(hx, hz), hz, rot, 1);
            dressBuilding(key, hx, W.heightAt(hx, hz), hz, rot, 1, sd ^ i);
          }
        }
        torchPost(x, W.heightAt(x, z), z);
      }
      else if (st.k === 'mosque') {
        var mk = 'mosque/small_' + (1 + (si % 2));
        if (MODELS[mk]) placeBuilt(mk, x, y, z, hashU(sd) * 6.283, 1);
      }
      else if (st.k === 'tower') {
        var tk = ['minaret/square', 'minaret/round', 'minaret/octagon'][si % 3];
        if (MODELS[tk]) placeBuilt(tk, x, y, z, 0, 1);
        torchPost(x + 3, W.heightAt(x + 3, z), z);
      }
      else if (st.k === 'ruin') {
        for (var rn = 0; rn < 4; rn++) {
          var ra = hashU((sd ^ (rn * 17)) | 0) * 6.283;
          var rx = x + Math.cos(ra) * (3 + rn * 2.4), rz = z + Math.sin(ra) * (3 + rn * 2);
          if (MODELS['bound/ruin']) placeBuilt('bound/ruin', rx, W.heightAt(rx, rz) - 0.1, rz, ra, 1);
        }
      }
      else if (st.k === 'graves') {
        for (var gn = 0; gn < 14; gn++) {
          var gx = x + (gn % 5) * 2.2 - 4.4 + hashU((sd ^ gn) | 0) * 0.8;
          var gz = z + Math.floor(gn / 5) * 2.8 - 2.8 + hashU((sd ^ (gn * 7)) | 0) * 0.8;
          if (MODELS.rock_small) place('rock_small', gx, W.heightAt(gx, gz) - 0.05, gz,
                                      0.5 + hashU((sd ^ (gn * 3)) | 0) * 0.3,
                                      hashU((sd ^ (gn * 11)) | 0) * 6.283);
        }
      }
      else if (st.k === 'quarry') {
        for (var qn = 0; qn < 6; qn++) {
          var qa = hashU((sd ^ (qn * 13)) | 0) * 6.283;
          var qx = x + Math.cos(qa) * (4 + qn * 2), qz = z + Math.sin(qa) * (4 + qn * 1.6);
          var qk = ['rock_a', 'rock_b', 'rock_c'][qn % 3];
          if (MODELS[qk]) place(qk, qx, W.heightAt(qx, qz) - 0.8, qz, 4 + qn, qa);
        }
      }
      else if (st.k === 'harbor') {
        if (MODELS['fence/plank_1']) {
          for (var hn = 0; hn < 3; hn++) {
            placeBuilt('fence/plank_1', x + hn * 3.6, y + 0.1, z, 0, 1);
          }
        }
        if (MODELS.p_crates) placeBuilt('p_crates', x + 2, y, z + 2, 0.6, 1);
        if (MODELS.p_barrels) placeBuilt('p_barrels', x - 2, y, z + 1.5, 1.9, 1);
      }
      else if (st.k === 'spring') {
        for (var sn = 0; sn < 8; sn++) {
          var sa = sn / 8 * 6.283;
          var sx2 = x + Math.cos(sa) * 3.2, sz2 = z + Math.sin(sa) * 3.2;
          if (MODELS['plant/reed_1']) place('plant/reed_1', sx2, W.heightAt(sx2, sz2) - 0.1, sz2,
                                            1.1 + hashU((sd ^ sn) | 0) * 0.5, sa);
        }
      }
      else if (st.k === 'spawn') {
        W.SPAWN = { x: x, z: z + 6 };
        /* any inspection visit (?at= or ?shot=) outranks the map's start */
        var qq = new URLSearchParams(location.search);
        if (W.camState && !qq.get('at') && !qq.get('shot')) {
          W.camState({ x: x, y: W.heightAt(x, z + 6) + 1.9, z: z + 6 });
        }
      }
    });
  }

  /* the bustan: a walled orchard. Giant trees five to seven storeys tall
     stand in loose rows over fig and olive, ringed by low mud walls. */
  function buildBustan(cx, cz) {
    var giants = ['tree/giant_1', 'tree/giant_2', 'tree/giant_3'];
    if (!MODELS[giants[0]]) return;
    /* the patriarchs, two loose rows */
    for (var i = 0; i < 7; i++) {
      var gx = cx + (i % 4) * 26 - 39 + hashU((i * 977) | 0) * 10;
      var gz = cz + Math.floor(i / 4) * 30 - 15 + hashU((i * 331) | 0) * 10;
      var gh = W.heightAt(gx, gz);
      var g = place(giants[i % 3], gx, gh - 0.3, gz, null,
                    hashU((i * 913) | 0) * 6.283, false, 'raw',
                    0.9 + hashU((i * 71) | 0) * 0.35);
      if (g) g.userData.col = W.addBox(gx, gh + 3.2, gz, 1.05, 3.2, 1.05, 0);
    }
    /* fig and olive fill the rows between */
    var FRUIT = ['tree/fig_1', 'tree/fig_2', 'tree/olive_1', 'tree/olive_2'];
    for (var f2 = 0; f2 < 15; f2++) {
      var fx = cx + (hashU((f2 * 419) | 0) - 0.5) * 96;
      var fz = cz + (hashU((f2 * 653) | 0) - 0.5) * 70;
      var fh = W.heightAt(fx, fz);
      if (fh < W.WATER_Y + 0.4) continue;
      var fg = place(FRUIT[f2 % 4], fx, fh - 0.25, fz, null,
                     hashU((f2 * 149) | 0) * 6.283, false, 'raw',
                     0.9 + hashU((f2 * 37) | 0) * 0.4);
      if (fg) fg.userData.col = W.addBox(fx, fh + 2, fz, 0.36, 2, 0.36, 0);
    }
    /* the low mud ring, gapped for the paths in */
    if (MODELS['bound/low']) {
      var hw2 = 52, hd2 = 40;
      for (var sw = -1; sw <= 1; sw += 2) {
        for (var wx2 = -hw2 + 2; wx2 < hw2 - 2; wx2 += 4.1) {
          if (Math.abs(wx2) < 5) continue;                 /* the gate gaps */
          var wz2 = cz + sw * hd2;
          placeBuilt('bound/low', cx + wx2, W.heightAt(cx + wx2, wz2) - 0.12, wz2, 0, 1);
        }
        for (var wz3 = -hd2 + 2; wz3 < hd2 - 2; wz3 += 4.1) {
          var wxe = cx + sw * hw2;
          placeBuilt('bound/low', wxe, W.heightAt(wxe, cz + wz3) - 0.12, cz + wz3, Math.PI / 2, 1);
        }
      }
    }
    torchPost(cx - 3.5, W.heightAt(cx - 3.5, cz - hd2), cz - 40);
    torchPost(cx + 3.5, W.heightAt(cx + 3.5, cz + hd2), cz + 40);
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

  /* grass cards: three crossed blades, eight triangles, thousands of them */
  var cardGeo = null, cardMat = null, reedGeo = null, reedMat = null;
  function makeCard(texUrl, w, h, tint) {
    var g = new T.PlaneGeometry(w, h);
    g.translate(0, h / 2, 0);
    var parts = [];
    for (var i = 0; i < 3; i++) {
      var q = g.clone();
      q.rotateY((i / 3) * Math.PI);
      parts.push(q);
    }
    var geo = mergeGeos(parts);
    var m = windify(new T.MeshStandardMaterial({
      map: W.tex(texUrl, true), alphaTest: 0.45, side: T.DoubleSide,
      roughness: 1, metalness: 0, color: tint
    }), '0.075');
    return { g: geo, m: m };
  }
  function mergeGeos(list) {
    var pos = [], uv = [], nrm = [], idx = [], off = 0;
    list.forEach(function (g) {
      var p = g.attributes.position, u = g.attributes.uv, n = g.attributes.normal;
      for (var i = 0; i < p.count; i++) {
        pos.push(p.getX(i), p.getY(i), p.getZ(i));
        uv.push(u.getX(i), u.getY(i));
        nrm.push(n.getX(i), n.getY(i), n.getZ(i));
      }
      var ix = g.index;
      for (var k = 0; k < ix.count; k++) idx.push(ix.getX(k) + off);
      off += p.count;
    });
    var out = new T.BufferGeometry();
    out.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    out.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
    out.setAttribute('normal', new T.Float32BufferAttribute(nrm, 3));
    out.setIndex(idx);
    return out;
  }

  /* what grows in one chunk */
  W.scatter = function (W, ci, cj, CH, seg) {
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

    /* the thick carpet of grass */
    if (!cardGeo) {
      var c1 = makeCard('assets/grass_card.png', 0.44, 0.34, 0xffffff);
      cardGeo = c1.g; cardMat = c1.m;
      var c2 = makeCard('assets/reed_card.png', 0.34, 1.15, 0xd2e0bd);
      reedGeo = c2.g; reedMat = c2.m;
    }
    /* the tuft wears the ground's own colour: dry gold where the land is dry,
       meadow green where it is green, drifting in the same big patches */
    var LT_DRY = [1.18, 0.98, 0.56], LT_GRN = [0.74, 0.84, 0.50];
    function landTint(x, z, g, sd) {
      var t = W.sstep(0.44, 0.76, g);
      var patch = 0.78 + 0.5 * W.fbm(x * 0.0021 + 3.1, z * 0.0021 - 8.7, 2);
      var j = 0.9 + hashU((sd ^ 0x51f) | 0) * 0.22;
      return [
        (LT_DRY[0] + (LT_GRN[0] - LT_DRY[0]) * t) * patch * j,
        (LT_DRY[1] + (LT_GRN[1] - LT_DRY[1]) * t) * patch * j,
        (LT_DRY[2] + (LT_GRN[2] - LT_DRY[2]) * t) * patch * j
      ];
    }
    function sowReeds(geo, m, count) {
      if (!count) return;
      var im = new T.InstancedMesh(geo, m, count);
      var n = 0;
      for (var i = 0; i < count; i++) {
        var sd = (ci * 73856093) ^ (cj * 19349663) ^ ((i + 9007) * 83492791);
        var rx = ox + hashU(sd) * CH, rz = oz + hashU(sd ^ 0x9e3779b9) * CH;
        var h = W.heightAt(rx, rz);
        var w = W.groundWeights(rx, rz, h);
        if (h < W.WATER_Y - 0.1 || h > W.WATER_Y + 2.2 || w.w < 0.55) continue;
        if (W.flatAt(rx, rz) > 0.30 || W.roadAt(rx, rz) > 0.35) continue;
        var sc = 0.8 + hashU(sd ^ 0x85ebca6b) * 0.7;
        dummy.position.set(rx, h - 0.12, rz);
        dummy.rotation.set(0, hashU(sd ^ 0xc2b2ae35) * 6.283, 0);
        dummy.scale.set(sc, sc, sc);
        dummy.updateMatrix();
        im.setMatrixAt(n++, dummy.matrix);
      }
      if (!n) { im.dispose(); return; }
      im.count = n; im.instanceMatrix.needsUpdate = true;
      W.scene.add(im); out.push(im);
    }

    function sowCards(geo, m, count, sMin, sMax) {
      if (!count) return;
      var im = new T.InstancedMesh(geo, m, count);
      var col3 = new T.Color();
      var n = 0;
      for (var i = 0; i < count; i++) {
        var sd = (ci * 73856093) ^ (cj * 19349663) ^ ((i + 5501) * 83492791);
        var rx = ox + hashU(sd) * CH, rz = oz + hashU(sd ^ 0x9e3779b9) * CH;
        var h = W.heightAt(rx, rz);
        var w = W.groundWeights(rx, rz, h);
        if (h < W.WATER_Y + 0.15 || w.g < 0.10 || w.r > 0.55) continue;
        /* thin out with the growth, never a hard edge */
        if (hashU(sd ^ 0x3d7) > 0.12 + 0.88 * w.g) continue;
        if (W.flatAt(rx, rz) > 0.30 || W.roadAt(rx, rz) > 0.35) continue;
        var sc = (sMin + hashU(sd ^ 0x85ebca6b) * (sMax - sMin)) * (0.55 + 0.7 * w.g);
        dummy.position.set(rx, h - 0.06, rz);
        dummy.rotation.set(0, hashU(sd ^ 0xc2b2ae35) * 6.283, 0);
        dummy.scale.set(sc, sc, sc);
        dummy.updateMatrix();
        im.setMatrixAt(n, dummy.matrix);
        var lt = landTint(rx, rz, w.g, sd);
        col3.setRGB(lt[0], lt[1], lt[2]);
        im.setColorAt(n, col3);
        n++;
      }
      if (!n) { im.dispose(); return; }
      im.count = n;
      im.instanceMatrix.needsUpdate = true;
      if (im.instanceColor) im.instanceColor.needsUpdate = true;
      W.scene.add(im);
      out.push(im);
    }

    var cb = W.biomeAt(ox + CH / 2, oz + CH / 2);
    var lush = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.25 && w.g > 0.45 && w.r < 0.5 && W.flatAt(x, z) < 0.3 && W.roadAt(x, z) < 0.35;
    };
    var dry = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.6 && w.g < 0.5 && W.flatAt(x, z) < 0.3 && W.roadAt(x, z) < 0.35;
    };
    var stony = function (x, z, h) {
      var w = W.groundWeights(x, z, h);
      return h > W.WATER_Y + 0.4 && w.r > 0.35 && W.flatAt(x, z) < 0.3 && W.roadAt(x, z) < 0.35;
    };

    /* blades first, then the modelled clumps on top of them */
    sowCards(cardGeo, cardMat, Math.round(7000 * (0.40 + cb.grass) * (W.vegScale || 1)), 1.0, 2.1);
    sowReeds(reedGeo, reedMat, Math.round(260 * (W.vegScale || 1)));
    var near = (seg === undefined) || seg >= 32;
    if (near) {
      sow('grass_a', Math.round(100 * (0.35 + cb.grass)), lush, 0.8, 1.7);
      sow('grass_b', Math.round(112 * (0.3 + cb.grass)), lush, 0.7, 1.5);
      /* flower meadows: a few strong clumps per chunk, each one colour,
         so the bloom reads as a patch of colour from far off */
      var FLK = ['fl_orange', 'fl_yellow', 'fl_purple', 'fl_white', 'fl_orange', 'fl_yellow'];
      var nCl = Math.round((2 + 3 * cb.grass) * (W.vegScale || 1));
      for (var fc = 0; fc < nCl; fc++) {
        var cs = (ci * 48611 + cj * 75377 + fc * 30011) | 0;
        var ccx = ox + hashU(cs) * CH, ccz = oz + hashU(cs ^ 0x77f) * CH;
        var ch2 = W.heightAt(ccx, ccz);
        if (!lush(ccx, ccz, ch2)) continue;
        var fkey = FLK[Math.floor(hashU(cs ^ 0x1b3) * FLK.length) % FLK.length];
        if (!MODELS[fkey]) continue;
        var per = 16 + Math.floor(hashU(cs ^ 0x9e1) * 18);
        for (var fi2 = 0; fi2 < per; fi2++) {
          var fa = hashU((cs ^ (fi2 * 7919)) | 0) * 6.283;
          var fr = Math.pow(hashU((cs ^ (fi2 * 104729)) | 0), 0.6) * 7.5;
          var fx2 = ccx + Math.cos(fa) * fr, fz2 = ccz + Math.sin(fa) * fr;
          var fh2 = W.heightAt(fx2, fz2);
          if (!lush(fx2, fz2, fh2)) continue;
          var fg2 = place(fkey, fx2, fh2 - 0.05, fz2,
                          0.72 + hashU((cs ^ (fi2 * 31)) | 0) * 0.45,
                          hashU((cs ^ (fi2 * 17)) | 0) * 6.283);
          if (fg2) out.push(fg2);
        }
      }
    }
    sow('bush_dry', Math.round(24 * (1 - cb.grass)), dry, 0.8, 1.7);
    sow('rock_d', Math.round(9 * (0.3 + cb.rock)), stony, 0.8, 2.2);
    sow('rock_small', Math.round(30 * (0.4 + cb.rock)), dry, 0.7, 1.9);
    sow('rock_small', Math.round(16 * (0.3 + cb.rock)), stony, 0.7, 1.9);
    if (near) {
      sow('plant/tuft_1', Math.round(38 * (0.3 + cb.grass)), lush, 0.9, 1.5);
      sow('plant/tuft_2', Math.round(32 * (0.3 + cb.grass)), lush, 0.9, 1.5);
      sow('plant/poppy_1', Math.round(11 * (0.2 + cb.grass)), lush, 0.9, 1.3);
      sow('plant/lavender_1', Math.round(9 * (0.2 + cb.grass)), lush, 0.9, 1.3);
      sow('plant/shrub_1', Math.round((8 + 26 * fMask) * (0.25 + cb.grass)), lush, 0.9, 1.5);
      sow('plant/blossom_1', Math.round(5 * (0.2 + cb.grass)), lush, 0.9, 1.4);
      sow('plant/thistle_1', Math.round(9 * (1 - cb.grass)), dry, 0.9, 1.3);
      sow('plant/aloe_1', Math.round(7 * (1 - cb.grass)), dry, 0.9, 1.3);
      sow('plant/agave_1', Math.round(6 * (1 - cb.grass)), dry, 0.9, 1.4);
      sow('plant/succulent_1', Math.round(6 * (0.3 + cb.rock)), stony, 0.9, 1.3);
      /* the green bank: reed and papyrus stand where the water table shows */
      var bank = function (x, z, h) {
        return h > W.WATER_Y - 0.15 && h < W.WATER_Y + 1.7 &&
               W.flatAt(x, z) < 0.3 && W.roadAt(x, z) < 0.35;
      };
      sow('plant/papyrus_1', 12, bank, 0.9, 1.3);
      sow('plant/reed_1', 16, bank, 0.9, 1.4);
    }

    /* trees and palms, sparse and deliberate. One stand per chunk: palms
       keep to the water veins, orchards keep to the grass -- a mixed clump
       of palms and planes is nothing that grows anywhere. */
    var zc = W.groundWeights(ox + CH / 2, oz + CH / 2, W.heightAt(ox + CH / 2, oz + CH / 2));
    var palmChunk = zc.w > 0.33;
    /* the light forests: big soft patches of woodland out in the country */
    var fMask = W.sstep(0.58, 0.74, W.fbm((ox + CH / 2) * 0.00052 + 91.3,
                                          (oz + CH / 2) * 0.00052 - 17.9, 3));
    if (W.mapForest) fMask = Math.max(fMask, W.mapForest(ox + CH / 2, oz + CH / 2));
    if (W.mapPalm && W.mapPalm(ox + CH / 2, oz + CH / 2) > 0.4) palmChunk = true;
    var townD2 = Math.hypot(ox + CH / 2, oz + CH / 2);
    if (townD2 < 210) fMask = 0;                    /* the town keeps its air */
    var forest = !palmChunk && fMask > 0.02;
    var treeN = Math.max(1, Math.round((9 * cb.grass + 3) * (1 + 5.5 * fMask) * (W.vegScale || 1)));
    for (var t = 0; t < treeN; t++) {
      var tx = ox + rng(ci + t, cj, 3.9) * CH, tz = oz + rng(ci, cj + t, 8.4) * CH;
      var th = W.heightAt(tx, tz);
      var w = W.groundWeights(tx, tz, th);
      if (th < W.WATER_Y + 0.5) continue;
      var key = null, sc = 1;
      var own = rng(tx, tz, 2.7);        /* the Blender-grown trees, true size */
      if (palmChunk) {
        if (w.w > 0.24) {
          if (own > 0.82) {              /* tamarisk holds the bank with them */
            key = 'tree/tamarisk_' + (own > 0.91 ? 2 : 1);
            sc = 0.9 + rng(tx, tz, 5.5) * 0.5;
          } else {
            key = 'palm'; sc = 8 + rng(tx, tz, 7) * 5;
          }
        }
      } else if (forest ? (w.g > 0.30) : (w.g > 0.55 && own > 0.5)) {
        var TS = ['tree/olive_1', 'tree/olive_2', 'tree/plane_1', 'tree/plane_2',
                  'tree/fig_1', 'tree/fig_2',
                  'tree/cypress_1', 'tree/cypress_2'];
        key = TS[Math.floor(rng(tx, tz, 3.3) * TS.length) % TS.length];
        sc = 0.9 + rng(tx, tz, 5.5) * 0.5;
      } else if (w.g > 0.62) {
        var pickN = rng(tx, tz, 1.1);
        key = pickN > 0.86 ? 'tree_anc' : (pickN > 0.5 ? 'tree_big_a' : 'tree_big_b');
        sc = pickN > 0.86 ? (24 + rng(tx, tz, 4) * 14) : (11 + rng(tx, tz, 2) * 8);
      } else if (rng(tx, tz, 6.6) > 0.72) {
        key = 'tree_small'; sc = 4 + rng(tx, tz, 5) * 3;
      }
      if (!key || !MODELS[key]) continue;
      var g = place(key, tx, th - 0.25, tz, sc, rng(tx, tz, 9) * 6.283);
      if (g) {
        if (key.indexOf('tree/') === 0) {
          g.userData.col = W.addBox(tx, th + 2.2, tz, 0.38, 2.2, 0.38, 0);
        } else {
          g.userData.col = W.addBox(tx, th + sc * 0.30, tz, sc * 0.045 + 0.25, sc * 0.30, sc * 0.045 + 0.25, 0);
        }
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

  /* a dense carpet of grass that travels with you · the only way a lawn reads */
  var lawn = null, lawnAt = new T.Vector3(9e9, 0, 9e9), LAWN_R = 52;
  function initLawn() {
    if (!cardGeo) {
      var c1 = makeCard('assets/grass_card.png', 0.44, 0.34, 0xd2dfbe);
      cardGeo = c1.g; cardMat = c1.m;
      var c2 = makeCard('assets/reed_card.png', 0.34, 1.15, 0xd2e0bd);
      reedGeo = c2.g; reedMat = c2.m;
    }
    var n = W.TIER === 2 ? 34000 : (W.TIER === 1 ? 11000 : 3000);
    lawn = new T.InstancedMesh(cardGeo, cardMat, n);
    lawn.name = 'lawn';
    lawn.frustumCulled = false;
    W.scene.add(lawn);
  }
  function refreshLawn(p) {
    if (!lawn) return;
    var dummy = new T.Object3D();
    var k = 0, tries = lawn.instanceMatrix.array.length / 16;
    for (var i = 0; i < tries; i++) {
      var sd = (Math.round(p.x / 8) * 73856093) ^ (Math.round(p.z / 8) * 19349663) ^ (i * 83492791);
      var a = hashU(sd) * 6.283;
      var r = Math.sqrt(hashU(sd ^ 0x9e3779b9)) * LAWN_R;
      var gx = p.x + Math.cos(a) * r, gz = p.z + Math.sin(a) * r;
      var h = W.heightAt(gx, gz);
      var w = W.groundWeights(gx, gz, h);
      if (h < W.WATER_Y + 0.12 || w.g < 0.20 || w.r > 0.65) continue;
      if (W.flatAt(gx, gz) > 0.30 || W.roadAt(gx, gz) > 0.35) continue;
      var sc = (0.55 + hashU(sd ^ 0x85ebca6b) * 0.7) * (0.55 + 0.7 * w.g);
      dummy.position.set(gx, h - 0.07, gz);
      dummy.rotation.set(0, hashU(sd ^ 0xc2b2ae35) * 6.283, 0);
      dummy.scale.set(sc, sc, sc);
      dummy.updateMatrix();
      lawn.setMatrixAt(k++, dummy.matrix);
    }
    lawn.count = k;
    lawn.instanceMatrix.needsUpdate = true;
    lawnAt.copy(p);
  }

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

  var smallTick = 0;
  W.tick = function (W, dt, t) {
    for (var i = 0; i < winds.length; i++) winds[i].value = t;
    var cp = W.cam.position;
    driveLights(t, dt);
    var pp = W.getPos();
    if (lawn && (Math.abs(pp.x - lawnAt.x) > 11 || Math.abs(pp.z - lawnAt.z) > 11)) refreshLawn(pp);
    tickFires(t, dt, cp);

    /* Small things are only drawn near the player. A town's worth of pots and
       barrels is more geometry than the buildings, and none of it reads from
       across the square. */
    if ((smallTick++ & 7) === 0) {
      for (var sI = 0; sI < SMALL.length; sI++) {
        var so = SMALL[sI];
        var sdx = so.position.x - cp.x, sdz = so.position.z - cp.z;
        so.visible = (sdx * sdx + sdz * sdz) < so.userData.far;
      }
    }
    for (var l = 0; l < lamps.length; l++) {
      var lp = lamps[l];
      if (lp.d2 > 60000) { lp.g.visible = false; continue; }
      lp.g.visible = true;
      lp.g.lookAt(cp);
      lp.g.material.opacity = 0.5 + 0.16 * lp.lit;
    }
    for (var d2 = 0; d2 < doors.length; d2++) {
      var dr = doors[d2];
      var target = dr.open ? -1.95 : 0;
      dr.ang += (target - dr.ang) * Math.min(1, dt * 4.6);
      if (dr.rot0 === undefined) dr.rot0 = dr.pivot.rotation.y;
      dr.pivot.rotation.y = dr.rot0 + dr.ang;
    }
  };

  /* ------------------------------------------------------------- build */
  /* A layout made in the editor. The editor writes a plain list of
     {k, p, r, s}; every entry is placed with its own collision, so what was
     put down there is what is solid here. */
  function buildLayout(list) {
    var keys = [];
    list.forEach(function (o) { if (keys.indexOf(o.k) < 0) keys.push(o.k); });
    Promise.all(keys.map(loadCollision));
    loadModels(keys, function () {
      var made = 0;
      list.forEach(function (o, idx) {
        var sc = o.s === undefined ? 1 : o.s;
        if (placeBuilt(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, sc)) {
          made++;
          /* doors, torch brackets and props hang off the exported spots */
          dressBuilding(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, sc, idx * 131 + 7);
        }
      });
      W.diag('');
      W.LAYOUT_COUNT = made;
      if (!made) W.diag('the layout is empty');
    });
    /* stand the player outside whatever was built */
    var minZ = 0;
    list.forEach(function (o) { if (o.p[2] < minZ) minZ = o.p[2]; });
    W.SPAWN = { x: 0, z: minZ - 40 };
    W.SPAWN_YAW = 0;
  }

  W.buildAll = function (W) {
    initMats();
    initFire();
    initPool();
    initLawn();

    var q = new URLSearchParams(location.search);
    if (q.get('layout')) {
      var raw = null;
      try { raw = localStorage.getItem('amirat.layout'); } catch (e) {}
      if (raw) {
        try {
          buildLayout(JSON.parse(raw));
          return;                       /* the editor's town replaces the built one */
        } catch (e) { W.diag('layout unreadable: ' + e.message); }
      } else {
        W.diag('nothing saved in the editor yet');
      }
    }

    var baseY = W.heightAt(TOWN.x, TOWN.z);
    TOWN.y = Math.max(baseY, W.WATER_Y + 7);
    W.addFlat(TOWN.x, TOWN.z, TOWNSQ * 1.46, TOWN.y, 80);

    /* The roads out of the gate. A road that leaves a gate in a dead straight
       line for a quarter of a kilometre reads as a drawn line on a map, so
       each one is laid as a chain of short legs that lean as they go. */
    (function roadOut(x0, z0, ang, legs, legLen, sway, half, seed) {
      var x = x0, z = z0, a = ang;
      for (var i = 0; i < legs; i++) {
        var sd = (seed + i * 40507) | 0;
        a += (hashU(sd) - 0.5) * sway;
        var nx = x + Math.sin(a) * legLen, nz = z + Math.cos(a) * legLen;
        W.addRoad(x, z, nx, nz, half * (1 - i / (legs * 1.7)));
        x = nx; z = nz;
        if (i === Math.floor(legs / 2)) {          /* a track branches off */
          var bA = a + (hashU(sd ^ 0x77) > 0.5 ? 0.9 : -0.9);
          var bx = x, bz = z;
          for (var k = 0; k < 4; k++) {
            var bSd = (sd ^ (k * 9173)) | 0;
            bA += (hashU(bSd) - 0.5) * 0.5;
            var ex = bx + Math.sin(bA) * legLen * 0.9, ez = bz + Math.cos(bA) * legLen * 0.9;
            W.addRoad(bx, bz, ex, ez, 4.6 - k * 0.6);
            bx = ex; bz = ez;
          }
        }
      }
    })(0, TOWNSQ - 10, 0, 7, 42, 0.44, 9.0, 8641);
    W.SPAWN = { x: 0, z: TOWNSQ + 52 };
    W.SPAWN_YAW = 0;
    W.SHOTS = {
      '1': { x: 0, z: TOWN.R + 70, yaw: 0, pitch: -0.02, h: 2.4 },
      '2': { x: 2, z: 40, yaw: 0.62, pitch: -0.02 },
      '3': { x: 0, z: -(TOWN.R - 3.2), yaw: 0, pitch: -0.20, h: 10.6 },
      '4': { x: 300, z: 400, yaw: 0, pitch: -0.03 },
      '5': { x: 430, z: -228, yaw: 0, pitch: -0.05 },
      '6': { x: -360, z: 306, yaw: 0, pitch: 0.02 },
      '7': { x: -40, z: -76, yaw: 3.14159, pitch: 0.05, h: 2.2 },
      '8': { x: 60, z: 300, yaw: 2.2, pitch: -0.16, h: 130, fly: true },
      '9': { x: 0, z: -(TOWN.R + 34), yaw: 3.14, pitch: 0.02, h: 2.4 },
      '10': { x: -72, z: 4, yaw: 1.6, pitch: 0.0, h: 2.2 },
      '11': { x: 6, z: 34, yaw: 0.0, pitch: -0.06, h: 2.3 },      /* the well market  */
      '12': { x: 0, z: TOWNSQ - 6, yaw: 0.0, pitch: -0.04, h: 2.5 }, /* inside the gate */
      '13': { x: 58, z: -32, yaw: 3.02, pitch: -0.04, h: 2.3 },   /* the east square  */
      '14': { x: 0, z: 470, yaw: 0.0, pitch: -0.10, h: 120, fly: true } /* the oasis from above */
    };

    buildTown();
    buildPalace(36, -34);
    buildLibrary(34, 36);
    buildHouses();

    Promise.all(BUILT.concat(WALL_KIT).concat(ALL_PROPS).map(loadCollision));
    loadModels(BUILT.concat(WALL_KIT).concat(ALL_PROPS).concat([
      'palm', 'lantern', 'mashaf', 'carpet',
      'tree_big_a', 'tree_big_b', 'tree_anc', 'tree_small', 'bush_dry',
      'fl_orange', 'fl_yellow', 'fl_purple', 'fl_white',
      'grass_a', 'grass_b', 'rock_a', 'rock_b', 'rock_c', 'rock_d', 'rock_small',
      'tree/olive_1', 'tree/olive_2', 'tree/plane_1', 'tree/plane_2',
      'tree/cypress_1', 'tree/cypress_2', 'tree/tamarisk_1', 'tree/tamarisk_2',
      'tree/fig_1', 'tree/fig_2',
      'plant/tuft_1', 'plant/tuft_2', 'plant/poppy_1', 'plant/lavender_1',
      'plant/thistle_1', 'plant/aloe_1', 'plant/agave_1', 'plant/succulent_1',
      'plant/papyrus_1', 'plant/reed_1', 'plant/shrub_1', 'plant/blossom_1',
      'tree/giant_1', 'tree/giant_2', 'tree/giant_3', 'bound/low']), function () {
        /* things that need the models */
        buildCitadel();
        buildSculptedHouses();
        dressSquares();
        /* the friday mosque, made in Blender: hall, dome, minaret, courtyard */
        if (MODELS.m_mosque) {
          var MX = -40, MZ = -34;
          placeBuilt('m_mosque', MX, TOWN.y, MZ, 0, 1.0);
          dressBuilding('m_mosque', MX, TOWN.y, MZ, 0, 1.0, 4242);
          [[-15, 14], [15, 14], [-15, -13], [15, -13]].forEach(function (t) {
            torch(MX + t[0], TOWN.y + 3.2, MZ + t[1], 0);
          });
          /* lamps hung between the courtyard piers */
          for (var q = -2; q <= 2; q++) {
            lamp(MX + q * 9, TOWN.y + 5.4, MZ + 37, 1.5);
          }
          lamp(MX, TOWN.y + 6.0, MZ, 1.8, false);   /* inside the dome, unseen */
          W.MOSQUE = { x: MX, z: MZ, y: TOWN.y };
        } else {
          buildMosque(-34, -30);
        }
        if (MODELS.p_well) { placeBuilt('p_well', 6, TOWN.y, 8, 0.4, 1.6); }
        lamp(6, TOWN.y + 3.4, 8, 1.3);

        buildCamp(430, -260, 4);
        buildCamp(-520, 300, 3);
        buildCave(-360, 250);
        buildOasis(300, 330);
        buildBustan(195, 245);
        buildMapSites();

        if (W.refreshVeg) W.refreshVeg();
      });
  };
})();
