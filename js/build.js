/* Amiratu al-Ulum · the built world
   Town walls and gates, mosque, palace, library, houses, camps, caves,
   fire and lamplight, and everything that grows. */
(function () {
  'use strict';
  var W = window.W;
  var T = THREE;

  var MODELS = {};
  W.MODELS = MODELS;             /* the card baker and the probes read these */
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
      /* A GLOW IS A DRAW CALL AND IT IS NEVER WELDED, because it flickers.
         Measured in a street with the market standing: 1,020 glow planes,
         459 of them on screen, 459 draw calls and a quarter of the frame -
         for a smear of light two pixels wide at that range. Past sixty
         metres the glow is switched off; the lantern and the torch it hangs
         on are welded stone and wood and stay exactly where they were, so
         nothing disappears, it just stops being lit from within. */
      /* fires still get the distance cut; their sheets cannot be welded */
      if (e.g && e.layers) {
        var want = e.d2 < 3600;
        if (e.g.visible !== want) e.g.visible = want;
      }
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

  /* groundY: where the light pool lies. A brazier on a minaret gallery is
     fifty metres above the ground, and without this its pool of firelight was
     painted on the earth far below. */
  function fire(x, y, z, scale, power, groundY) {
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
    pool.position.y = -y + (groundY === undefined ? W.heightAt(x, z) : groundY) + 0.06;
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
      /* how much of the fire is worth drawing at this distance: all of it
         close to, one tongue of flame from across the town. A light must
         still be seen from far - his rule - so the flame never goes out,
         only its layers do. */
      var lod = f.d2 < 2600 ? 2 : (f.d2 < 17000 ? 1 : 0);

      /* each layer runs the sheet at its own speed, so the flame never loops
         visibly and the core dances faster than the body */
      for (var L = 0; L < f.layers.length; L++) {
        if (L > 0) {
          var want = (lod === 2) || (lod === 1 && L === 1);
          if (f.layers[L].mesh.visible !== want) f.layers[L].mesh.visible = want;
          if (!want) continue;
        }
        var ly = f.layers[L];
        var fr = Math.floor((t * ly.sp + ly.off) % FRAMES);
        ly.tex.offset.y = 1 - (fr + 1) / FRAMES;
        ly.mesh.lookAt(cp.x, ly.mesh.getWorldPosition(new T.Vector3()).y, cp.z);
        var s = 0.93 + 0.14 * Math.sin(t * (5 + L * 2) + f.ph + L);
        ly.mesh.scale.set(s, 0.92 + 0.16 * f.lit, 1);
      }

      f.pool.material.opacity = 0.24 + 0.18 * f.lit;
      f.pool.scale.setScalar(0.94 + 0.1 * f.lit);

      if (f.pool && f.pool.visible !== (lod > 0)) f.pool.visible = (lod > 0);

      /* embers drift up, fade, and start again */
      if (f.d2 < 4000) {
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
  /* ONE GEOMETRY AND ONE MATERIAL FOR EVERY LAMP IN THE WORLD. Each lamp used
     to build its own MeshBasicMaterial, which meant the weld grouped them by
     material and every group had exactly one member - and a group of one is
     skipped as not worth welding. So a thousand identical planes each kept
     their own draw call for want of a shared material. Nothing is ever
     changed on this material: the flicker rides on the pooled point light. */
  var glowGeo = null, glowMat = null;
  function lamp(x, y, z, power, model, reach) {
    if (!glowGeo) {
      glowGeo = new T.PlaneGeometry(1.5, 1.5);
      glowMat = new T.MeshBasicMaterial({ map: W.tex('assets/glow.png', true),
        color: 0xffd08a, transparent: true, blending: T.AdditiveBlending,
        depthWrite: false, toneMapped: false, opacity: 0.7 });
    }
    var g = new T.Mesh(glowGeo, glowMat);
    g.position.set(x, y, z);
    /* this one may be welded: it is a fixed plane, not a billboard that has to
       be re-aimed every frame */
    g.userData.weldGlow = 1;
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

  /* the leaf with its planks already in it, one geometry per door size */
  var boardedGeos = {}, bandGeos = {}, knobGeo = null;
  function boardedLeaf(w, h) {
    var key = w.toFixed(2) + 'x' + h.toFixed(2);
    if (boardedGeos[key]) return boardedGeos[key];
    var parts = [leafGeometry(w, h).clone()];
    for (var pl = 1; pl < 4; pl++) {
      var rib = new T.BoxGeometry(0.045, h * 0.94, 0.03);
      rib.translate(w * pl / 4, h * 0.47, 0.075);
      parts.push(rib);
    }
    boardedGeos[key] = mergeGeos(parts);
    return boardedGeos[key];
  }
  function bandGeometry(w, h) {
    var key = w.toFixed(2) + 'x' + h.toFixed(2);
    if (!bandGeos[key]) {
      var g = new T.BoxGeometry(w * 0.92, 0.09, 0.035);
      g.translate(w / 2, h * 0.28, 0.08);
      bandGeos[key] = g;
    }
    return bandGeos[key];
  }
  function knobGeometry() {
    if (!knobGeo) knobGeo = new T.SphereGeometry(0.06, 8, 6);
    return knobGeo;
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
    /* A DOOR WAS SIX MESHES: a leaf, three ribs, a ledger and a knob, and a
       door cannot be welded into the town because it swings. A hundred and
       forty doors was eight hundred and fifty loose objects - by far the
       largest group of unwelded meshes in the world. The leaf and its ribs
       share one material and turn together on the same hinge, so they are one
       geometry now, built once per door size and cached. Six meshes down to
       three, and the ribbed geometry is made once for the whole town. */
    var leaf = new T.Mesh(painted ? leafGeometry(w, h) : boardedLeaf(w, h), mat);
    pivot.add(leaf);
    if (!painted) {
      var band = new T.Mesh(bandGeometry(w, h), M.iron || M.wood);
      pivot.add(band);
    }
    var knob = new T.Mesh(knobGeometry(), M.gold);
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
  var COLRAD = {};
  var COLJSON = {}, SPOTJSON = {}, DOORJSON = {}, FXJSON = {};
  /* Which models carry a collision, door or firefly file. Without this the
     game asked for all three for every model - nearly six hundred 404s
     standing in front of the models that actually have to arrive, on a
     browser that opens six connections. That was the ten to twenty seconds
     of dark before the world appeared. */
  var SIDE = null, COLBUNDLE = null;
  /* ONE request for every model's collision. Measured on the live host: 117
     separate little json fetches, each paying a real round trip, spread over
     forty seconds. The bytes are nothing - 0.2 MB for all of them - it is the
     requests that cost. */
  var sidePromise = Promise.all([
    fetch(W.bust('assets/models/index.json'))
      .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
    fetch(W.bust('assets/models/collision.json'))
      .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
  ]).then(function (both) {
    var j = both[0];
    COLBUNDLE = both[1];
    if (j) {
      SIDE = { col: {}, door: {}, fx: {} };
      ['col', 'door', 'fx'].forEach(function (k) {
        (j[k] || []).forEach(function (n) { SIDE[k][n] = 1; });
      });
    }
    return SIDE;
  });

  function has(kind, name) {
    return !SIDE || SIDE[kind][name];      /* no index: fall back to asking */
  }

  function loadCollisionInner(name) {
    return Promise.all([
      (COLBUNDLE && COLBUNDLE[name] ? Promise.resolve(COLBUNDLE[name])
        : (has('col', name) ? fetch(W.bust('assets/models/' + name + '.col.json'))
            .then(function (r) { return r.ok ? r.json() : null; }) : Promise.resolve(null)))
        .then(function (j) {
          if (!j) return;
          COLJSON[name] = j.boxes;
          if (j.spots) SPOTJSON[name] = j.spots;
          /* how much ground this model needs, measured off its own boxes,
             so houses of different shapes are spaced by what they are */
          var r = 0;
          for (var q = 0; q < j.boxes.length; q++) {
            var bb = j.boxes[q];
            r = Math.max(r, Math.hypot(Math.abs(bb.c[0]) + bb.h[0],
                                       Math.abs(bb.c[2]) + bb.h[2]));
          }
          COLRAD[name] = r;
        })
        .catch(function () {}),
      (has('door', name) ? fetch(W.bust('assets/models/' + name + '.door.json'))
        .then(function (r) { return r.ok ? r.json() : null; }) : Promise.resolve(null))
        .then(function (j) { if (j && j.doors) DOORJSON[name] = j.doors; })
        .catch(function () {}),
      (has('fx', name) ? fetch(W.bust('assets/models/' + name + '.fx.json'))
        .then(function (r) { return r.ok ? r.json() : null; }) : Promise.resolve(null))
        .then(function (j) { if (j) FXJSON[name] = j; })
        .catch(function () {})
    ]);
  }

  function loadCollision(name) {
    /* wait for the index, then ask only for what is there */
    return sidePromise.then(function () { return loadCollisionInner(name); });
  }

  /* ------------------------------------------- doors and fireflies that a
     placed MODEL brings with it: the qasr's thirty-five swinging doors, its
     drifting lights. Exported as sidecar data by the generator. */
  var FIREFLIES = [], flyMats = null;
  function spawnModelDoors(name, bx, by, bz, brot, scale) {
    var defs = DOORJSON[name];
    if (!defs) return;
    var c = Math.cos(brot), s2 = Math.sin(brot);
    for (var i = 0; i < defs.length; i++) {
      var dd = defs[i];
      var wx = bx + (dd.x * scale) * c + (dd.z * scale) * s2;
      var wz = bz - (dd.x * scale) * s2 + (dd.z * scale) * c;
      var fx = dd.fx * c + dd.fz * s2;
      var fz = -dd.fx * s2 + dd.fz * c;
      /* the leaf runs along the wall: rot maps +x to (cos, -sin) */
      var tx = -fz, tz = fx;
      var rot = Math.atan2(-tz, tx);
      var w2 = dd.w * scale / 2, hh = dd.h * scale;
      var dl = door(wx - tx * w2, by + dd.y0 * scale, wz - tz * w2, w2, hh, rot);
      var dr2 = door(wx + tx * w2, by + dd.y0 * scale, wz + tz * w2, w2, hh, rot + Math.PI);
      if (dr2) dr2.dir = 1;
      if (dl) dl.dir = -1;
    }
  }
  /* Whatever a placed model asks the engine to light or to grow: its fires
     (the minaret braziers, the garden torches) and its garden (real trees,
     flowers and grass - a welded palace cannot carry a tree). */
  function spawnModelExtras(name, bx, by, bz, brot, scale) {
    var j = FXJSON[name];
    if (!j) return;
    var c = Math.cos(brot), s2 = Math.sin(brot);
    (j.fires || []).forEach(function (ff) {
      var wx = bx + (ff.x * scale) * c + (ff.z * scale) * s2;
      var wz = bz - (ff.x * scale) * s2 + (ff.z * scale) * c;
      fire(wx, by + ff.y * scale, wz, (ff.s || 1) * scale, ff.p || 1,
           by + (ff.g === undefined ? 0 : ff.g) * scale);
    });
    (j.lamps || []).forEach(function (ll) {
      var wx = bx + (ll.x * scale) * c + (ll.z * scale) * s2;
      var wz = bz - (ll.x * scale) * s2 + (ll.z * scale) * c;
      /* model:false - the palace carries its own lantern; this is the LIGHT.
         Short reach on purpose: a point light is not stopped by a wall, and a
         room lamp that carries thirty metres lights the street through it. */
      lamp(wx, by + ll.y * scale, wz, (ll.p || 0.55) * scale, false,
           (ll.r || 8) * scale);
    });
    (j.cover || []).forEach(function (bd2, bi) {
      sowBed(bd2, bx, by, bz, brot, scale, bi);
    });
    var cover = [];
    (j.garden || []).forEach(function (gg) {
      if (gg.k.charAt(0) === '@') { cover.push(gg); return; }
      var wx = bx + (gg.x * scale) * c + (gg.z * scale) * s2;
      var wz = bz - (gg.x * scale) * s2 + (gg.z * scale) * c;
      var g = placeBuilt(gg.k, wx, by + gg.y * scale, wz, (gg.r || 0) + brot,
                         (gg.s || 1) * scale);
      /* a tree is worth drawing from across the court; a tuft of grass is not */
      if (g) {
        g.userData.far = /tree\//.test(gg.k) ? 40000 : 4900;
        SMALL.push(g);
      }
    });
    if (cover.length) plantCover(cover, bx, by, bz, brot, scale);
  }

  /* THE GARDEN'S GROUND COVER.
     He asked for ten times the flowers. A poppy MODEL is 2,780 triangles, so
     ten thousand of them is thirty million triangles and no machine draws
     that. The flowers and the grass in the beds are CARDS instead - the same
     photographs the meadow is sown with, six triangles apiece, alpha cut and
     carrying a little light of their own so they hold their colour at night -
     and every picture is drawn ONCE as an instanced mesh. Ten thousand of
     those is sixty thousand triangles and one draw call per picture. */
  var coverCard = null;

  /* A BED, SOWN FROM ITS SEED. The palace writes down a rectangle and how many
     flowers and blades belong in it; the positions are made here. Fifty
     thousand of them written into the sidecar was a four megabyte download for
     one garden, and it is the same garden either way because the hash is
     fixed. */
  function sowBed(b, bx, by, bz, brot, scale, bi) {
    if (!coverCard) coverCard = makeCard('assets/grass_card.png', 0.62, 0.52, 0x9db986);
    var c = Math.cos(brot), s2 = Math.sin(brot);
    var dummy = new T.Object3D();
    var groups = {};                       /* picture -> array of instances */
    function put(key, wx, wy, wz, rot, sc) {
      (groups[key] = groups[key] || []).push([wx, wy, wz, rot, sc]);
    }
    function place1(i, kind) {
      var sd = ((b.seed * 2654435761) ^ (i * 40503) ^ (kind * 19349663)) | 0;
      var u = hashU(sd) - 0.5, v = hashU(sd ^ 0x9e37) - 0.5;
      var lx = u * b.w * scale, lz = v * b.d * scale;
      var ox = b.x * scale, oz = b.z * scale;
      var wx = bx + (ox + lx) * c + (oz + lz) * s2;
      var wz = bz - (ox + lx) * s2 + (oz + lz) * c;
      var rot = hashU(sd ^ 0x77) * 6.283 + brot;
      if (kind === 0) {
        var col = FLOWER_KEYS[Math.floor(hashU(sd ^ 0x51ab) * 4) & 3];
        var files = FLOWER_CARDS[col];
        var f = files[Math.floor(hashU(sd ^ 0x1234) * files.length) % files.length];
        put('fl|' + f, wx, by + b.y * scale, wz, rot,
            (0.85 + hashU(sd ^ 0x2b1d) * 1.05) * scale);
      } else {
        put('gr', wx, by + b.y * scale, wz, rot,
            (0.55 + hashU(sd ^ 0x2b1d) * 0.60) * scale);
      }
    }
    for (var i = 0; i < b.fl; i++) place1(i, 0);
    for (var k = 0; k < b.gr; k++) place1(k, 1);
    Object.keys(groups).forEach(function (key) {
      var items = groups[key];
      var geo, mat;
      if (key === 'gr') { geo = coverCard.g; mat = coverCard.m; }
      else { var cd = flowerCard(key.slice(3)); geo = cd.g; mat = cd.m; }
      /* A CARD'S OWN BOUNDS ARE A HAND'S WIDTH, so an instanced mesh of
         fifty thousand of them either culls itself away the moment its first
         card leaves the screen, or - with culling off - draws the half of the
         garden behind your head. The geometry is cloned per bed and given the
         BED's bounding sphere, so a quarter you have turned your back on
         costs nothing. Measured: 30 ms in the court became 14. */
      var g2 = geo.clone();
      g2.boundingSphere = new T.Sphere(
        new T.Vector3(bx + (b.x * scale) * c + (b.z * scale) * s2,
                      by + b.y * scale + 1.0,
                      bz - (b.x * scale) * s2 + (b.z * scale) * c),
        Math.hypot(b.w, b.d) * scale * 0.55 + 2.0);
      var im = new T.InstancedMesh(g2, mat, items.length);
      for (var q = 0; q < items.length; q++) {
        var it = items[q];
        dummy.position.set(it[0], it[1], it[2]);
        dummy.rotation.set(0, it[3], 0);
        dummy.scale.set(it[4], it[4], it[4]);
        dummy.updateMatrix();
        im.setMatrixAt(q, dummy.matrix);
      }
      im.instanceMatrix.needsUpdate = true;
      im.frustumCulled = true;
      im.castShadow = false;
      W.scene.add(im);
    });
  }

  function plantCover(list, bx, by, bz, brot, scale) {
    var c = Math.cos(brot), s2 = Math.sin(brot);
    /* the blade sheet is a straw-and-green photograph; white leaves it acid
       green next to the palace stone, so the garden's grass is tinted to a
       watered, slightly grey green */
    if (!coverCard) coverCard = makeCard('assets/grass_card.png', 0.62, 0.52, 0x9db986);
    var bins = {};
    for (var i = 0; i < list.length; i++) {
      var g = list[i], key;
      if (g.k === '@gr') key = 'gr';
      else {
        var files = FLOWER_CARDS[g.c] || FLOWER_CARDS.white;
        key = 'fl|' + files[i % files.length];
      }
      (bins[key] = bins[key] || []).push(g);
    }
    var dummy = new T.Object3D(), made = 0;
    Object.keys(bins).forEach(function (key) {
      var items = bins[key];
      var geo, mat, base;
      if (key === 'gr') { geo = coverCard.g; mat = coverCard.m; base = 1.0; }
      else {
        var cd = flowerCard(key.slice(3));
        geo = cd.g; mat = cd.m; base = 1.0;
      }
      var im = new T.InstancedMesh(geo, mat, items.length);
      for (var k = 0; k < items.length; k++) {
        var it = items[k];
        var wx = bx + (it.x * scale) * c + (it.z * scale) * s2;
        var wz = bz - (it.x * scale) * s2 + (it.z * scale) * c;
        var sc = (it.s || 1) * scale * base;
        dummy.position.set(wx, by + it.y * scale, wz);
        dummy.rotation.set(0, (it.r || 0) + brot, 0);
        dummy.scale.set(sc, sc, sc);
        dummy.updateMatrix();
        im.setMatrixAt(k, dummy.matrix);
      }
      im.instanceMatrix.needsUpdate = true;
      /* one card is the whole geometry, so its own bounds are a hand's width;
         give the mesh the bed's bounds or it culls itself away the moment the
         middle of the court leaves the screen */
      im.frustumCulled = false;
      im.castShadow = false;
      W.scene.add(im);
      made++;
    });
    if (W.diag) W.diag('sowed ' + list.length + ' cards in ' + made + ' meshes');
  }

  function spawnModelFx(name, bx, by, bz, brot, scale) {
    var defs = FXJSON[name] && FXJSON[name].fireflies;
    if (!defs) return;
    if (!flyMats) {
      var mkm = function (hex) {
        return new T.SpriteMaterial({
          map: W.tex('assets/glow.png', true), color: hex, transparent: true,
          opacity: 0.85, blending: T.AdditiveBlending, depthWrite: false
        });
      };
      flyMats = [mkm(0xffd28a), mkm(0xc890ef)];
    }
    var c = Math.cos(brot), s2 = Math.sin(brot);
    for (var i = 0; i < defs.length; i++) {
      var ff = defs[i];
      var wx = bx + (ff.x * scale) * c + (ff.z * scale) * s2;
      var wz = bz - (ff.x * scale) * s2 + (ff.z * scale) * c;
      var sp = new T.Sprite(flyMats[ff.c ? 1 : 0].clone());
      var sc3 = 0.55 + hashU((i * 7919) | 0) * 0.5;
      sp.scale.set(sc3, sc3, 1);
      sp.position.set(wx, by + ff.y * scale, wz);
      W.scene.add(sp);
      FIREFLIES.push({ s: sp, x: wx, y: by + ff.y * scale, z: wz,
                       p1: hashU((i * 131) | 0) * 6.283,
                       p2: hashU((i * 733) | 0) * 6.283,
                       p3: hashU((i * 1543) | 0) * 6.283 });
    }
  }
  /* EVERY MODEL THE TOWN STANDS UP IS WRITTEN DOWN HERE, in exactly the shape
     the editor saves and the game reads back: {k, p:[x,y,z], r, s}. That is
     what makes the built town importable - the procedural pass and the editor
     speak the same language, so the town can be handed from one to the other
     without anything being rebuilt or guessed. */
  var PLACED_LOG = [];
  W.PLACED_LOG = PLACED_LOG;
  /* THE GROUND IS PART OF THE TOWN. It was levelled for it (addFlat) and the
     streets were painted into it (addRoad); neither is a model, so neither
     lands in the piece list. They are recorded separately and replayed when
     the layout is loaded, or the imported town stands on raw grass with no
     streets under it. */
  /* THE TWO BUILDINGS THAT ARE NOT MODELS. The domed hall and the library are
     built out of boxes and spheres in this file, not made in Blender, so they
     can never ride in a piece list - the editor would not know what to do with
     the name and would quietly drop them, and the first time he saved they
     would be gone for good. They travel here instead, in a store the editor
     never touches, and are rebuilt when the layout loads.
     (The right fix in the end is to make them real models like the mosque.) */
  var GROUND_LOG = { flats: [], roads: [], structs: [] };
  W.GROUND_LOG = GROUND_LOG;
  (function () {
    var rawFlat = W.addFlat, rawRoad = W.addRoad;
    W.addFlat = function (x, z, r, y, blend) {
      GROUND_LOG.flats.push([+x.toFixed(1), +z.toFixed(1), +r.toFixed(1),
                             +y.toFixed(2), +(blend || 40).toFixed(1)]);
      return rawFlat.apply(W, arguments);
    };
    W.addRoad = function (x0, z0, x1, z1, half) {
      GROUND_LOG.roads.push([+x0.toFixed(1), +z0.toFixed(1), +x1.toFixed(1),
                             +z1.toFixed(1), +(half || 7).toFixed(2)]);
      return rawRoad.apply(W, arguments);
    };
  })();
  /* THE ONE THING THE LIST MUST NOT CONTAIN is the props a building dresses
     ITSELF with. Those come out of the model's own spots, and the loader runs
     that same dressing again for every piece it places - so logging them puts
     every cushion and water jug in the town down twice. Measured: the town
     welded 3,870 meshes, and reloading its own export welded 5,654. */
  var dressing = 0;
  function placeBuilt(name, x, y, z, rot, scale) {
    var g = place(name, x, y, z, null, rot, false, 'raw', scale);
    if (!g) return null;
    if (!dressing) {
      PLACED_LOG.push({ k: name, p: [+x.toFixed(2), +y.toFixed(2), +z.toFixed(2)],
                        r: +(rot || 0).toFixed(4), s: +(scale || 1).toFixed(3) });
    }
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
  /* ---------------- one texture per picture, one material per look -------
     Every model packs its own copy of the wall photograph, so the same few
     pictures arrived 594 times over and cost 452 MB of texture memory -
     more than an integrated GPU will hold, so the driver swaps them in and
     out and the frame time climbs from 26 ms to nearly a second. That is the
     lag. Each picture is hashed as its file arrives, only the first copy is
     kept, and then materials describing the same look share one object -
     which also lets the weld put them all in one batch. */
  var TEXBANK = {}, MATBANK = {}, SHARED = { tex: 0, mat: 0 };

  function hashBytes(u8, from, len) {
    var h = 0x811c9dc5, step = Math.max(1, Math.floor(len / 4096));
    for (var i = 0; i < len; i += step) {
      h ^= u8[from + i];
      h = (h * 0x01000193) >>> 0;
    }
    return len + '_' + (h >>> 0).toString(16);
  }

  function imageHashes(buf) {
    try {
      var dv = new DataView(buf);
      if (dv.getUint32(0, true) !== 0x46546c67) return null;
      var jsonLen = dv.getUint32(12, true);
      var json = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 20, jsonLen)));
      var p = 20 + jsonLen, binOff = -1;
      while (p < buf.byteLength) {
        var clen = dv.getUint32(p, true), ctype = dv.getUint32(p + 4, true);
        if (ctype === 0x004e4942) { binOff = p + 8; break; }
        p += 8 + clen + ((4 - clen % 4) % 4);
      }
      if (binOff < 0 || !json.images) return null;
      var u8 = new Uint8Array(buf), out = [];
      for (var i = 0; i < json.images.length; i++) {
        var im = json.images[i];
        if (im.bufferView === undefined) { out.push(null); continue; }
        var bv = json.bufferViews[im.bufferView];
        out.push(hashBytes(u8, binOff + (bv.byteOffset || 0), bv.byteLength));
      }
      return { hashes: out, json: json };
    } catch (e) { return null; }
  }

  var TEX_SLOTS = ['map', 'normalMap', 'roughnessMap', 'emissiveMap', 'aoMap', 'alphaMap'];

  function shareTextures(gltf, info) {
    if (!info || !gltf.parser || !gltf.parser.associations) return;
    var assoc = gltf.parser.associations, json = info.json, seen = {};
    gltf.scene.traverse(function (o) {
      if (!o.isMesh || !o.material) return;
      var mats = Array.isArray(o.material) ? o.material : [o.material];
      for (var k = 0; k < mats.length; k++) {
        var m = mats[k];
        if (!m || seen[m.uuid]) continue;
        seen[m.uuid] = 1;
        for (var j = 0; j < TEX_SLOTS.length; j++) {
          var slot = TEX_SLOTS[j], t = m[slot];
          if (!t) continue;
          var a = assoc.get(t);
          if (!a || a.textures === undefined) continue;
          var src = json.textures[a.textures].source;
          var h = info.hashes[src];
          if (!h) continue;
          h = slot + ':' + h;
          if (TEXBANK[h] && TEXBANK[h] !== t) {
            t.dispose();
            m[slot] = TEXBANK[h];
            SHARED.tex++;
          } else if (!TEXBANK[h]) {
            TEXBANK[h] = t;
          }
        }
      }
    });
  }

  function shareMaterials(gltf) {
    gltf.scene.traverse(function (o) {
      if (!o.isMesh || !o.material || Array.isArray(o.material)) return;
      var m = o.material;
      var key = [m.type, m.name, m.color ? m.color.getHexString() : '-',
                 m.roughness, m.metalness,
                 m.map ? m.map.uuid : '-', m.normalMap ? m.normalMap.uuid : '-',
                 m.roughnessMap ? m.roughnessMap.uuid : '-',
                 m.emissive ? m.emissive.getHexString() : '-', m.emissiveIntensity,
                 m.transparent ? 1 : 0, m.alphaTest, m.vertexColors ? 1 : 0, m.side,
                 m.flatShading ? 1 : 0].join('|');
      if (MATBANK[key] && MATBANK[key] !== m) {
        o.material = MATBANK[key];
        m.dispose();
        SHARED.mat++;
      } else if (!MATBANK[key]) {
        MATBANK[key] = m;
      }
    });
  }
  W.shareCounts = function () { return SHARED; };

  function loadModels(list, done) {
    loader = new T.GLTFLoader();
    var queue = list.slice(), active = 0, left = list.length, MAX = 10;
    var loadEl = document.getElementById('load');

    function finish() {
      if (--left === 0) {
        if (loadEl) loadEl.style.display = 'none';
        var _t0 = performance.now();
        done();
        W.BUILD_MS = Math.round(performance.now() - _t0);
        W.MODELS_IN = true;      /* fixed-viewpoint capture waits for this */
        /* The world is standing now: show it. The weld is a few seconds of
           pure arithmetic that nobody should sit in the dark for - it runs on
           the next tick and the town simply gets cheaper to draw when it
           lands. */
        setTimeout(function () {
          var _t1 = performance.now();
          try { if (W.crunch) W.crunch(); } catch (e) { if (W.diag) W.diag('crunch: ' + e.message); }
          W.CRUNCH_MS = Math.round(performance.now() - _t1);
        }, 50);
        if (!W.LOAD_MS) {
          W.LOAD_MS = Math.round(performance.now());
          if (W.diag) W.diag('world up in ' + (W.LOAD_MS / 1000).toFixed(1) + 's');
        }
        /* ?export=1 - hand the built town to the editor and stop. It waits a
           moment for the second wave so the trees and rocks come with it. */
        try {
          if (new URLSearchParams(location.search).get('export') && !W.__exported) {
            W.__exported = true;
            setTimeout(function () { W.sendTownToEditor(true); }, 4200);
          }
        } catch (e) {}
        /* SECOND WAVE. What the world can stand up without: the plants, the
           rocks, the ordinary trees. They arrive after the world does and sow
           themselves when they land, so nobody waits in the dark for them.
           (This used to carry fifteen blossom giants at about thirty
           megabytes as well. They are out of the world now.) */
        if (!W.__wave2) {
          W.__wave2 = true;
          setTimeout(function () {
            var late = ['bush_dry', 'fl_orange', 'fl_yellow', 'fl_purple', 'fl_white',
                        'grass_a', 'grass_b', 'rock_a', 'rock_b', 'rock_c', 'rock_d',
                        'rock_small',
                        'plant/tuft_1', 'plant/tuft_2', 'plant/poppy_1', 'plant/lavender_1',
                        'plant/thistle_1', 'plant/aloe_1', 'plant/agave_1',
                        'plant/succulent_1', 'plant/papyrus_1', 'plant/reed_1',
                        'plant/shrub_1', 'plant/blossom_1'];
            ['olive', 'plane', 'cypress', 'tamarisk', 'fig', 'pine'].forEach(function (k) {
              for (var v = 1; v <= 5; v++) {
                var key = 'tree/' + k + '_' + v;
                if (!MODELS[key]) late.push(key);
              }
            });
            late = late.concat(W.BLOSSOM_ROW);
            Promise.all(late.map(loadCollision)).then(function () {
              loadModels(late, function () {
                try { pigmentFlowers(); } catch (e) {}
                try { if (W.refreshVeg) W.refreshVeg(); } catch (e) {}
              });
            });
          }, 1200);
        }
      } else if (loadEl && loadEl.style.display !== 'none') {
        loadEl.textContent = 'Building the world… ' + Math.round((1 - left / list.length) * 100) + '%';
      }
      pump();
    }

    function fetchOne(name, tries) {
      active++;
      var onFail = function () {
        active--;
        if (tries < 2) { setTimeout(function () { fetchOne(name, tries + 1); }, 500 + tries * 900); }
        else { W.diag('model missing: ' + name); finish(); }
      };
      fetch(W.bust('assets/models/' + name + '.glb')).then(function (res) {
        if (!res.ok) throw new Error('http ' + res.status);
        return res.arrayBuffer();
      }).then(function (buf) {
        var info = imageHashes(buf);
        loader.parse(buf, '', function (g) {
        active--;
        g.scene.traverse(function (o) {
          if (o.isMesh) {
            o.castShadow = true; o.receiveShadow = true;
            /* Bounds computed from the geometry we actually have. A canopy
               written as one big vertex list can arrive with bounds from the
               file that do not enclose it, and then the renderer decides the
               tree is off screen and stops drawing it -- which is why trees
               vanished when you walked up to one or looked straight at it. */
            if (o.geometry) {
              o.geometry.computeBoundingSphere();
              o.geometry.computeBoundingBox();
            }
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
        shareTextures(g, info);
        shareMaterials(g);
        MODELS[name] = g.scene;
        finish();
        }, onFail);
      }).catch(onFail);
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
  /* A HOUSE IS NOT A STOREROOM. The first cut was chests and crates against
     every wall, because those were half the list. What actually lines the wall
     of a room somebody lives in is the water jar, the baskets, the pots, the
     bedding rolled up, the books - and one chest. */
  /* what a household leaves against the outside of its own wall */
  var HOUSE_LEAN = ['p_firewood', 'p_basket', 'p_jars', 'p_waterjug', 'p_crates',
                    'p_sacks', 'p_ropecoil', 'p_stones', 'p_barrel', 'p_broom',
                    'p_bench', 'p_plantpot'];
  var ROOM_WALL = ['p_waterjug', 'p_jars', 'p_basket', 'p_basket', 'p_pot',
                   'p_cushions', 'p_books', 'p_scrolls', 'p_stool', 'p_broom',
                   'p_chest', 'p_sacks'];
  var ROOM_MID = ['p_table', 'p_cushions', 'p_stool', 'p_inkset', 'p_bowl',
                  'p_oillamp'];

  /* PROPS_ROOM WAS NEVER IN THIS LIST. Every piece of furniture a house was
     supposed to be furnished with - the carpet, the cushions, the books, the
     stool, the chest - was never fetched, so propOn looked it up, found no
     model, and quietly returned null. Measured in the built town: 152 houses
     and ZERO carpets. The few things that did appear in rooms only appeared
     because they were also on the roof or street lists. */
  var ALL_PROPS = PROPS_ROOF.concat(PROPS_ARMS, PROPS_STREET, PROPS_ROOM,
                                    ROOM_WALL, ROOM_MID, HOUSE_LEAN,
                                    ['p_brazier', 'p_well', 'p_torch', 'p_torchpost',
                                     'p_bread'])
    .filter(function (k, i, a) { return a.indexOf(k) === i; });

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

  /* what stands against a wall, and what belongs in the middle */
  /* is this spot free at THIS height? the room rectangle covers the internal
     walls as well as the floor, so every piece of furniture has to ask */
  function clearAt(x, y, z, r) {
    if (!W.nearBoxes) return true;
    var bs = W.nearBoxes(x, z);
    for (var i = 0; i < bs.length; i++) {
      var b = bs[i];
      if (b.y1 < y + 0.15 || b.y0 > y + 1.5) continue;
      if (Math.abs(x - b.x) < b.hx + r && Math.abs(z - b.z) < b.hz + r) return false;
    }
    return true;
  }

  function dressRoom(sp, bx, by, bz, brot, scale, seedBase, si) {
    var c = Math.cos(brot), s2 = Math.sin(brot);
    var rx = sp.r[0] * scale, rz = sp.r[1] * scale;
    var ly = sp.c[1] * scale;
    function world(lx, lz) {
      return [bx + lx * c + lz * s2, bz - lx * s2 + lz * c];
    }
    var seed0 = (seedBase * 2654435761) ^ (si * 40503);

    /* the carpet, in the middle, turned with the room */
    var mid = world(sp.c[0] * scale, sp.c[2] * scale);
    /* the carpet asks for less room than the check first demanded: it lies
       flat, so it only has to clear what stands ON the floor */
    if (clearAt(mid[0], by + ly, mid[1], 0.7) && MODELS.p_carpet) {
      placeBuilt('p_carpet', mid[0], by + ly, mid[1], brot, Math.min(1.5, scale * 1.1));
    }
    /* and what sits on it */
    for (var m = 0; m < 2; m++) {
      var ms = (seed0 ^ (m * 7919)) | 0;
      var mx = sp.c[0] * scale + (hashU(ms) - 0.5) * rx * 0.7;
      var mz = sp.c[2] * scale + (hashU(ms ^ 0x51) - 0.5) * rz * 0.7;
      var w2 = world(mx, mz);
      if (!clearAt(w2[0], by + ly, w2[1], 0.36)) continue;
      propOn(ROOM_MID, ms, w2[0], by + ly, w2[1], hashU(ms ^ 0x77) * 6.283, 1);
    }

    /* THE WALLS. Walk the inside of the rectangle and set things down facing
       into the room, skipping whatever is solid. */
    var placed = 0;
    for (var e = 0; e < 4; e++) {
      var along = (e % 2 === 0) ? rx : rz;
      var stepN = Math.max(2, Math.round(along / 1.5));
      for (var k = 0; k < stepN; k++) {
        var sd = (seed0 ^ (e * 104729 + k * 40503)) | 0;
        if (hashU(sd) < 0.26) continue;
        var t = (k + 0.5) / stepN * 2 - 1;          /* -1 .. 1 along the wall */
        var lx, lz, face;
        if (e === 0) { lx = t * rx * 0.86; lz = -rz * 0.84; face = 0; }
        else if (e === 1) { lx = rx * 0.84; lz = t * rz * 0.86; face = -Math.PI / 2; }
        else if (e === 2) { lx = t * rx * 0.86; lz = rz * 0.84; face = Math.PI; }
        else { lx = -rx * 0.84; lz = t * rz * 0.86; face = Math.PI / 2; }
        lx += sp.c[0] * scale; lz += sp.c[2] * scale;
        var w3 = world(lx, lz);
        if (!clearAt(w3[0], by + ly, w3[1], 0.32)) continue;
        propOn(ROOM_WALL, sd, w3[0], by + ly, w3[1], brot + face, 1);
        placed++;
        if (placed > 9) break;
      }
      if (placed > 9) break;
    }

    /* the light of the room, so a window reads as a window and not a hole.
       Short reach on purpose: a point light is not stopped by a wall, and a
       room lamp that carries thirty metres lights the street through it. */
    if (hashU(seed0 ^ 0x2b1d) > 0.24) {
      lamp(mid[0], by + ly + 1.5, mid[1], 0.55, false, 6.5);
    }
  }

  /* fill one building's flat places with a different set each time */
  function dressBuilding(name, bx, by, bz, brot, scale, seedBase) {
    var spots = SPOTJSON[name];
    if (!spots) return;
    dressing++;
    try { dressBuildingInner(name, bx, by, bz, brot, scale, seedBase, spots); }
    finally { dressing--; }
  }
  function dressBuildingInner(name, bx, by, bz, brot, scale, seedBase, spots) {
    var c = Math.cos(brot), s2 = Math.sin(brot);
    for (var i = 0; i < spots.length; i++) {
      var sp = spots[i];
      if (sp.k === 'climb') {
        /* the model brought a ladder with it: put it where the model stands */
        var lx = (sp.c[0] * scale) * c + (sp.c[2] * scale) * s2;
        var lz = -(sp.c[0] * scale) * s2 + (sp.c[2] * scale) * c;
        var y0 = by + (sp.c[1] - sp.h[1]) * scale;
        var y1 = by + (sp.c[1] + sp.h[1]) * scale;
        if (W.addLadder) W.addLadder(bx + lx, y0, y1, bz + lz,
                                     Math.max(sp.h[0], sp.h[2]) * scale + 0.45);
        continue;
      }
      if (sp.k === 'door') {
        /* a leaf on its hinge, turned to the face it was exported on */
        var hx = (sp.c[0] * scale) * c + (sp.c[2] * scale) * s2;
        var hz = -(sp.c[0] * scale) * s2 + (sp.c[2] * scale) * c;
        var face = brot + ((sp.f || 0) * Math.PI / 180);
        door(bx + hx, by + sp.c[1] * scale, bz + hz,
             sp.r[0] * scale * 0.97, sp.r[1] * scale * 0.97, face);
        continue;
      }
      /* A ROOM IS FURNISHED ROUND ITS WALLS. Three props scattered at random
         over the whole ground floor gave every house three things standing in
         the middle of the floor with nothing against the walls - which is not
         how anybody has ever lived. A room in a house like this is a carpet in
         the middle and everything else pushed to the edges: the chest against
         one wall, the water jar by the door, the lamp on a shelf, the bedding
         rolled in a corner.
         Nothing is placed without asking the world whether that spot is free,
         because the room rectangle covers the internal walls too. */
      if (sp.k === 'room') { dressRoom(sp, bx, by, bz, brot, scale, seedBase, i); continue; }
      var n = (sp.k === 'balcony' ? 2 : 4);
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


  /* ------------------------------------------------------------- the souk
     A market in a town like this is not a ring of tables round an open yard.
     It is a STREET: shops down both sides, the lane kept clear to walk, and
     the trades sitting TOGETHER - a stretch of cloth, then spice, then bread,
     then the potters. You know where you are in it by what is being sold.

     Twenty trade models were already made and none of them was being used;
     the squares were dressed with a plain stall and an awning and nothing
     else. This lays the whole kit along the main lanes: the booth at the back
     against the buildings, its table or its mat out in front of it toward the
     street, its goods stacked behind, and a rack or a barrow where there is
     room. */
  var TRADES = [
    { n: 'cloth',   booth: 'stall/booth_cloth',
      front: ['stall/rack_cloth', 'stall/trestle_basket'],
      mat: 'stall/mat_basket',   goods: ['p_crates', 'p_basket', 'p_sacks'] },
    { n: 'spice',   booth: 'stall/booth_spice',
      front: ['stall/trestle_basket', 'stall/mat_spice'],
      mat: 'stall/mat_spice',    goods: ['p_sacks', 'p_basket', 'p_jars'] },
    { n: 'metal',   booth: 'stall/booth_metal',
      front: ['stall/trestle_metal', 'stall/rack_rope'],
      mat: 'stall/mat_rope',     goods: ['p_barrels', 'p_crates', 'p_stones'] },
    { n: 'bread',   booth: 'stall/canopy_bread',
      front: ['stall/trestle_basket', 'stall/barrow_grain'],
      mat: 'stall/mat_basket',   goods: ['p_sacks', 'p_basket', 'p_bread'] },
    { n: 'fruit',   booth: 'stall/canopy_fruit',
      front: ['stall/barrow_fruit', 'stall/trestle_basket'],
      mat: 'stall/mat_basket',   goods: ['p_crates', 'p_basket', 'p_pot'] },
    { n: 'grain',   booth: 'stall/canopy_grain',
      front: ['stall/barrow_grain', 'stall/trestle_basket'],
      mat: 'stall/mat_basket',   goods: ['p_sacks', 'p_sacks', 'p_barrels'] },
    { n: 'pottery', booth: 'stall/leanto_pottery',
      front: ['stall/trestle_pottery', 'stall/mat_basket'],
      mat: 'stall/mat_basket',   goods: ['p_jars', 'p_pot', 'p_waterjug'] },
    { n: 'wood',    booth: 'stall/leanto_wood',
      front: ['stall/trestle_basket', 'stall/rack_rope'],
      mat: 'stall/mat_rope',     goods: ['p_firewood', 'p_crates', 'p_ropecoil'] },
    { n: 'baskets', booth: 'stall/canopy_spice',
      front: ['stall/mat_basket', 'stall/trestle_basket'],
      mat: 'stall/mat_basket',   goods: ['p_basket', 'p_basket', 'p_ropecoil'] }
  ];
  var SOUK_KEYS = (function () {
    var k = [];
    TRADES.forEach(function (t) {
      [t.booth, t.mat].concat(t.front).forEach(function (m) {
        if (k.indexOf(m) < 0) k.push(m);
      });
    });
    return k;
  })();
  W.SOUK_KEYS = SOUK_KEYS;

  /* A SHOP MUST NOT BE A BLACK SLAB. There are fourteen real lights in the
     whole world - they follow whichever flames are nearest, and two hundred
     shops cannot each have one. A booth is a closed box, so at night, with no
     flame beside it, every face of it goes to black and the market reads as a
     row of coffins.
     The flowers already solved this: give the sheet a little light of its own
     so its colour survives the dark. The awnings and the goods get the same
     treatment - not a glow, just enough that the cloth is still cloth at
     midnight - and the real lights carry on doing the close work. */
  function warmStalls() {
    (W.SOUK_KEYS || []).concat(['p_stall', 'p_awning']).forEach(function (k) {
      var m = MODELS[k];
      if (!m || m.userData.warmed) return;
      m.userData.warmed = true;
      var seen = {};
      m.traverse(function (o) {
        if (!o.isMesh || !o.material || seen[o.material.uuid]) return;
        seen[o.material.uuid] = 1;
        var mat = o.material;
        if (!mat.map) return;
        mat.emissive = new T.Color(0xffffff);
        mat.emissiveMap = mat.map;
        mat.emissiveIntensity = 0.17;
        mat.needsUpdate = true;
      });
    });
  }

  /* is there room here? a stall must not stand inside a wall or on a doorstep */
  function clearGround(x, z, r) {
    if (!W.nearBoxes) return true;
    var bs = W.nearBoxes(x, z), y = W.heightAt(x, z);
    for (var i = 0; i < bs.length; i++) {
      var b = bs[i];
      if (b.y1 < y + 0.3 || b.y0 > y + 2.6) continue;   /* under foot or overhead */
      if (Math.abs(x - b.x) < b.hx + r && Math.abs(z - b.z) < b.hz + r) return false;
    }
    return true;
  }

  function buildSouk() {
    if (!MODELS['stall/booth_cloth']) return 0;
    warmStalls();
    /* the widest lanes carry the market; the little alleys stay quiet */
    var lanes = WAYS.filter(function (w) { return w.half >= 2.3; })
      .map(function (w) {
        return { w: w, len: Math.hypot(w.bx - w.ax, w.bz - w.az) };
      })
      .filter(function (o) { return o.len > 10; })
      .sort(function (a, b) { return b.len - a.len; })
      .slice(0, 22);

    var made = 0, run = 0, trade = 0;
    lanes.forEach(function (o, li) {
      var w = o.w;
      var ux = (w.bx - w.ax) / o.len, uz = (w.bz - w.az) / o.len;
      var nx = -uz, nz = ux;                       /* across the lane */
      var STEP = 4.2;
      var n = Math.floor(o.len / STEP);
      for (var i = 0; i < n; i++) {
        var t = (i + 0.5) * STEP;
        var cx = w.ax + ux * t, cz = w.az + uz * t;
        for (var sd = -1; sd <= 1; sd += 2) {
          var seed = ((li * 92821 + i * 7919 + sd * 331) | 0);
          if (hashU(seed) < 0.46) continue;        /* not every yard is a shop */
          /* the trades sit together: the same one for a run of stalls */
          if (run <= 0) { trade = Math.floor(hashU(seed ^ 0x5ab) * TRADES.length) % TRADES.length;
                          run = 5 + Math.floor(hashU(seed ^ 0x77) * 5); }
          run--;
          var T = TRADES[trade];
          var off = w.half + 1.5;
          var bx = cx + nx * sd * off, bz = cz + nz * sd * off;
          if (!clearGround(bx, bz, 1.7)) continue;
          var y = W.heightAt(bx, bz);
          /* the shop faces the street it stands on */
          var face = Math.atan2(-nx * sd, -nz * sd);
          if (!placeBuilt(T.booth, bx, y, bz, face, 1)) continue;
          made++;
          /* its table or its mat, out in front toward the lane */
          var fx = bx - nx * sd * 1.85, fz = bz - nz * sd * 1.85;
          var fk = T.front[Math.floor(hashU(seed ^ 0x11) * T.front.length) % T.front.length];
          if (clearGround(fx, fz, 0.9)) placeBuilt(fk, fx, W.heightAt(fx, fz), fz, face, 1);
          /* goods stacked behind the shop, where the wall is */
          for (var g = 0; g < 1; g++) {
            var gsd = (seed ^ (g * 40503)) | 0;
            var gx = bx + nx * sd * (1.3 + hashU(gsd) * 0.9) + ux * (hashU(gsd ^ 3) - 0.5) * 2.2;
            var gz = bz + nz * sd * (1.3 + hashU(gsd) * 0.9) + uz * (hashU(gsd ^ 3) - 0.5) * 2.2;
            if (clearGround(gx, gz, 0.7)) {
              propOn(T.goods, gsd, gx, W.heightAt(gx, gz), gz, hashU(gsd ^ 9) * 6.283, 1);
            }
          }
          /* A SHOP THAT IS NOT LIT IS A BLACK SLAB. A booth is a closed box
             and at night, with nothing burning near it, that is exactly how it
             reads. Every one of them carries its own lamp under the awning -
             cheap, one sprite each, and the light pool picks the nearest few -
             and a real torch stands over the lane every sixth shop. */
          /* NOT ONE LAMP PER SHOP. Lamps are protected from the weld, so each
             one is its own draw call - two hundred shops put the town over
             fourteen hundred calls on its own. The warmed cloth carries the
             look; a real light hangs every fourth shop. */
          if (made % 4 === 1) lamp(bx - nx * sd * 0.5, y + 2.05, bz - nz * sd * 0.5, 0.62, false, 7.5);
          if (made % 12 === 5) {
            torchPost(cx + nx * sd * (w.half + 0.5), W.heightAt(cx, cz),
                      cz + nz * sd * (w.half + 0.5));
          }
        }
      }
    });
    if (W.diag && made) W.diag('the souk: ' + made + ' shops');
    return made;
  }

  /* A market stands in every open place: stalls under awnings around the rim,
     the goods stacked behind them, a brazier for the cold. Without this the
     squares read as empty yards, which is the one thing a town square is not. */
  function dressSquares() {
    var GOODS = ['p_jars', 'p_crates', 'p_sacks', 'p_barrels', 'p_basket',
                 'p_pot', 'p_waterjug', 'p_ropecoil', 'p_firewood', 'p_stones'];
    for (var q = 0; q < SQUARES.length; q++) {
      var sq = SQUARES[q];
      var stalls = 7 + Math.floor(hashU((q * 7717) | 0) * 5);
      for (var i = 0; i < stalls; i++) {
        var sd = (q * 92821 + i * 51203) | 0;
        var a = (i / stalls) * 6.283 + hashU(sd) * 0.6;
        var rr = sq.r * (0.72 + hashU(sd ^ 0x3) * 0.34);
        var sx = sq.x + Math.cos(a) * rr, sz = sq.z + Math.sin(a) * rr;
        if (W.roadAt && W.roadAt(sx, sz) > 0.55) continue;
        var face = Math.atan2(sq.x - sx, sq.z - sz);      /* face the square */
        var y = W.heightAt(sx, sz);
        /* the open square gets the same trade kit as the lanes, so a stall
           on the square and a shop in the souk belong to the same market */
        var TQ = TRADES[Math.floor(hashU(sd ^ 0x2ab) * TRADES.length) % TRADES.length];
        var pick = hashU(sd ^ 0x9);
        var key = pick > 0.62 ? TQ.booth
                : (pick > 0.34 ? TQ.front[0]
                : (pick > 0.18 ? 'p_stall' : 'p_awning'));
        if (!MODELS[key]) key = 'p_stall';
        placeBuilt(key, sx, y, sz, face, 1);
        if (pick > 0.62 && MODELS[TQ.mat]) {
          var mx2 = sx - Math.sin(face) * 1.9, mz2 = sz - Math.cos(face) * 1.9;
          placeBuilt(TQ.mat, mx2, W.heightAt(mx2, mz2), mz2, face, 1);
        }
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

    /* the ring road just inside the wall: without it the whole outer band is
       out of reach of any way, and the town stands in the middle of its own
       walls with a bare ring around it */
    var RG = S - 20;
    var ring = [[-RG, -RG], [RG, -RG], [RG, RG], [-RG, RG], [-RG, -RG]];
    for (var rr = 0; rr < 4; rr++) {
      wander(ring[rr][0], ring[rr][1], ring[rr + 1][0], ring[rr + 1][1],
             3.6, 30, 3, 8117 + rr * 131);
    }
    /* and four ways out from the middle to meet it */
    wander(well[0], well[1], -RG + 14, -RG + 26, 3.4, 34, 3, 9127);
    wander(well[0], well[1], RG - 20, -RG + 18, 3.4, 34, 3, 9137);
    wander(plazaB[0], plazaB[1], -RG + 18, RG - 22, 3.4, 34, 3, 9151);
    wander(plazaC[0], plazaC[1], RG - 16, RG - 18, 3.4, 34, 3, 9161);

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
    var RAD = 8.4 * HOUSE_SCALE * 0.62;    /* fallback, if a model has no boxes */
    function radOf(key) {
      return (COLRAD[key] ? COLRAD[key] * 0.62 : 8.4 * 0.62) * HOUSE_SCALE;
    }

    function keepOut(x, z) {
      if (Math.hypot(x + 40, z + 34) < 36) return true;   /* the mosque */
      if (Math.hypot(x + 40, z - 3) < 27) return true;    /* its courtyard */
      if (Math.hypot(x - 6, z - 8) < 14) return true;     /* the well square */
      if (Math.abs(x) > S - 14 || Math.abs(z) > S - 14) return true;
      return false;
    }

    /* Scatter candidates over the whole town, keep the ones that fit. The
       leftovers between them become the alleys and dead ends. */
    /* A TOWN IS NOT A FIELD OF HUTS. From the air this read as scattered
       boxes with ten to thirty metres of bare ground between them, which is
       the one thing a walled town never looks like: ground inside a wall is
       expensive, so people build on it, share walls, and leave only what they
       must to walk through. The grid is finer now so more sites are tried, and
       most pairs are allowed to crowd right up against each other. */
    var STEP = 4.3;
    for (var gz = -S + 18; gz < S - 18; gz += STEP) {
      for (var gx = -S + 18; gx < S - 18; gx += STEP) {
        var sd = ((gx * 73856093) ^ (gz * 19349663)) | 0;
        var x = gx + (hashU(sd) - 0.5) * STEP * 1.6;
        var z = gz + (hashU(sd ^ 0x9e3) - 0.5) * STEP * 1.6;
        if (keepOut(x, z)) continue;

        var near = distToWays(x, z);
        /* it must stand clear of the roadway, but close enough to be served
           (a cheap first cut; the model's own footprint is checked below) */
        if (near.d < RAD * 0.45) continue;
        if (near.d > 32) continue;

        var key = BUILT[idx % BUILT.length];
        if (!MODELS[key]) { idx++; continue; }
        var myR = radOf(key);
        if (near.d < myR * 0.72) continue;

        var ok = true;
        for (var i = 0; i < placed.length; i++) {
          var pl = placed[i];
          /* every pair is judged by both footprints, so a long range keeps
             its neighbours further off than a narrow tower does */
          /* in the reference, houses share walls as often as they stand
             apart: nearly half are allowed to crowd right up to a neighbour,
             which is what makes blocks and narrow alleys instead of a field
             of separate boxes */
          var need = (myR + pl[2]) * (hashU(sd ^ (i * 7919)) > 0.42 ? 0.62 : 0.94);
          if (Math.hypot(x - pl[0], z - pl[1]) < need) { ok = false; break; }
        }
        if (!ok) continue;
        idx++;
        /* turn to face whatever way runs nearest, but never squarely */
        var facing = Math.atan2(near.at.px - x, near.at.pz - z) + (hashU(sd ^ 0xabc) - 0.5) * 0.5;
        var g = placeBuilt(key, x, Y, z, facing, HOUSE_SCALE);
        if (!g) continue;
        placed.push([x, z, myR]);
        made++;
        dressBuilding(key, x, Y, z, facing, HOUSE_SCALE, idx * 31 + 7);

        var fx = Math.sin(facing), fz = Math.cos(facing);
        /* one house in nine keeps a torch by its door; the rest get a lamp,
           which is one sprite instead of a fire's five meshes and its light */
        if (idx % 9 === 0) torch(x + fx * 7.2, Y + 2.9, z + fz * 7.2, facing);
        else if (idx % 3 === 0) lamp(x + fx * 6.4, Y + 3.3, z + fz * 6.4, 1.0, false);
        for (var q = 0; q < 2; q++) {
          var sd2 = (idx * 7919 + q * 104729) | 0;
          if (hashU(sd2) < 0.52) continue;
          propOn(PROPS_STREET, sd2,
                 x + fx * (8.2 + hashU(sd2 ^ 3) * 2.4) + fz * (hashU(sd2 ^ 7) - 0.5) * 7,
                 Y,
                 z + fz * (8.2 + hashU(sd2 ^ 3) * 2.4) - fx * (hashU(sd2 ^ 7) - 0.5) * 7,
                 hashU(sd2 ^ 9) * 6.283, 1);
        }
        /* AND THINGS AGAINST THE HOUSE ITSELF. The citadel wall already had
           its stone and firewood stacked along it, but the houses had nothing
           at their feet, so every street read as buildings standing on a
           parade ground. A lane in a town like this is half blocked by what
           people have left against their own walls: the firewood, the water
           jar by the door, a stack of baskets, a broken crate nobody has moved
           in a year. Each one asks whether the spot is free first. */
        for (var L2 = 0; L2 < 5; L2++) {
          var ls = (idx * 51203 + L2 * 92821) | 0;
          if (hashU(ls) < 0.55) continue;
          var la = hashU(ls ^ 0x3f) * 6.283;
          var lr = myR * (0.92 + hashU(ls ^ 0x5c) * 0.20);
          var lxp = x + Math.cos(la) * lr, lzp = z + Math.sin(la) * lr;
          if (!clearGround(lxp, lzp, 0.75)) continue;
          propOn(HOUSE_LEAN, ls, lxp, Y, lzp, la + Math.PI / 2, 1);
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

  /* The war workshop's proving ground: one arranged outpost far out in the
     flat desert, shown only under ?site=1, so none of it touches the world
     until it is deployed for real. Objects only -- never crew. */
  function buildTestSite() {
    var SITE = ['war/ak', 'war/rpg', 'war/mortar', 'war/dshk',
                'mil/hesco', 'mil/sandbags', 'mil/twall', 'mil/jersey',
                'mil/chainlink', 'mil/boom_barrier', 'mil/checkpoint',
                'mil/watchtower_wood', 'mil/watchtower_metal',
                'veh/humvee', 'veh/landrover', 'veh/technical',
                'veh/wreck_car', 'veh/wreck_truck'];
    var CX = 800, CZ = -800;
    Promise.all(SITE.map(loadCollision));
    loadModels(SITE, function () {
      var Y = function (x, z) { return W.heightAt(x, z); };
      /* a lit standard so the site is findable at night */
      torchPost(CX, Y(CX, CZ), CZ);
      lamp(CX, Y(CX, CZ) + 4, CZ, 2.0);
      /* the perimeter: a line of hescos, then T-walls, with a gate */
      for (var i = 0; i < 5; i++) {
        var hx = CX - 24 + i * 10;
        if (i !== 2) placeBuilt('mil/hesco', hx, Y(hx, CZ - 20), CZ - 20, 0, 1);
      }
      for (var t = 0; t < 4; t++) {
        var tx = CX - 18 + t * 12;
        placeBuilt('mil/twall', tx, Y(tx, CZ + 20), CZ + 20, Math.PI / 2, 1);
      }
      /* the gate: boom barrier + checkpoint + two jerseys */
      placeBuilt('mil/boom_barrier', CX - 4, Y(CX - 4, CZ - 20), CZ - 20, 0, 1);
      placeBuilt('mil/checkpoint', CX + 4, Y(CX + 4, CZ - 24), CZ - 24, Math.PI, 1);
      placeBuilt('mil/jersey', CX - 6, Y(CX - 6, CZ - 16), CZ - 16, 0.3, 1);
      placeBuilt('mil/jersey', CX + 6, Y(CX + 6, CZ - 16), CZ - 16, -0.3, 1);
      /* the towers at two corners */
      placeBuilt('mil/watchtower_wood', CX - 26, Y(CX - 26, CZ - 22), CZ - 22, 0.6, 1);
      placeBuilt('mil/watchtower_metal', CX + 26, Y(CX + 26, CZ - 22), CZ - 22, -0.6, 1);
      /* sandbag positions and a chainlink run inside */
      placeBuilt('mil/sandbags', CX - 14, Y(CX - 14, CZ + 4), CZ + 4, 0.2, 1);
      placeBuilt('mil/sandbags', CX + 12, Y(CX + 12, CZ + 6), CZ + 6, -0.4, 1);
      for (var f = 0; f < 3; f++) {
        placeBuilt('mil/chainlink', CX - 30, Y(CX - 30, CZ - 6 + f * 2.5), CZ - 6 + f * 2.5, Math.PI / 2, 1);
      }
      /* the motor pool: the vehicles parked in a row inside the wire */
      var veh = ['veh/humvee', 'veh/landrover', 'veh/technical', 'veh/wreck_car', 'veh/wreck_truck'];
      for (var v = 0; v < veh.length; v++) {
        var vx = CX - 20 + v * 10;
        placeBuilt(veh[v], vx, Y(vx, CZ), CZ, Math.PI * 0.5 + (v % 2) * 0.1, 1);
      }
      /* the weapons on a display line, raised on low blocks, lit */
      var wpn = ['war/ak', 'war/rpg', 'war/dshk', 'war/mortar'];
      for (var w = 0; w < wpn.length; w++) {
        var wx = CX - 6 + w * 4;
        var wz = CZ + 12;
        box(1.6, 0.5, 0.7, wx, Y(wx, wz) + 0.35, wz, M.stone2, 0);   // a stand
        placeBuilt(wpn[w], wx, Y(wx, wz) + 0.75, wz, 0, wpn[w] === 'war/mortar' ? 1 : 1.6);
      }
      lamp(CX, Y(CX, CZ + 12) + 2.4, CZ + 12, 1.4);
      W.SITE = { x: CX, z: CZ, y: Y(CX, CZ) };
      W.diag('');
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
    /* the oasis keeps its palms; the old normalised giants that used to ring
       it are out of the world with the rest of them. Proper trees at their
       true size stand here instead. */
    for (var t = 0; t < 5; t++) {
      var ta = t * 1.35 + 0.7, tr = 44 + (t % 3) * 9;
      var tx = cx + Math.cos(ta) * tr, tz = cz + Math.sin(ta) * tr;
      var ty = W.heightAt(tx, tz);
      if (ty < W.WATER_Y + 0.3) continue;
      var key = ['tree/fig_2', 'tree/plane_3', 'tree/tamarisk_1'][t % 3];
      if (MODELS[key]) place(key, tx, ty - 0.3, tz, null, ta, false, 'raw', 1.0);
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
  /* ground-cover shading law: blades take the terrain's own light. Normals
     all point up, so a tuft and the soil beneath it read as one surface. */
  function normalsUp(g) {
    var na = g.attributes.normal;
    if (!na) return g;
    for (var i = 0; i < na.count; i++) na.setXYZ(i, 0, 1, 0);
    na.needsUpdate = true;
    return g;
  }
  function vegParts(key) {
    /* every mesh of the model, each as its own instanced layer */
    var ck = key + '#parts';
    if (VEG[ck]) return VEG[ck];
    var src = MODELS[key];
    if (!src) return null;
    var metas = [];
    src.updateWorldMatrix(true, true);
    /* shared origin: the whole model's ground centre, so parts stay aligned */
    var bbAll = new T.Box3().setFromObject(src);
    var cx0 = (bbAll.min.x + bbAll.max.x) / 2;
    var cz0 = (bbAll.min.z + bbAll.max.z) / 2;
    var y0 = bbAll.min.y;
    src.traverse(function (o) {
      if (!o.isMesh) return;
      var g = o.geometry.clone();
      g.applyMatrix4(o.matrixWorld);
      g.translate(-cx0, -y0, -cz0);
      var mm = o.material.clone();
      mm.side = T.DoubleSide;
      mm.metalness = 0;
      if (mm.transparent || mm.alphaMap || (mm.map && mm.alphaTest === 0)) { mm.alphaTest = 0.42; mm.transparent = false; }
      windify(mm, 0.05);
      metas.push({ g: g, m: mm });
    });
    if (!metas.length) return null;
    var height = bbAll.max.y - bbAll.min.y || 1;
    return (VEG[ck] = { parts: metas, height: height });
  }

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
    /* a blade under moonlight is not black; give the sheet a little light of
       its own or the whole meadow reads as tar. It must be GREEN light: a
       white lift on a straw-coloured sheet turns the field to gold crumbs. */
    m.emissive = new T.Color(0x4e6247);
    m.emissiveMap = m.map;
    m.emissiveIntensity = 0.11;
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
      /* NOT EVERY GEOMETRY IS INDEXED. An ExtrudeGeometry - which is what a
         door leaf is - has index === null, and reading .count off it throws
         and takes the whole world build down with it. An unindexed geometry
         is simply its vertices in order. */
      var ix = g.index;
      if (ix) { for (var k = 0; k < ix.count; k++) idx.push(ix.getX(k) + off); }
      else { for (var k2 = 0; k2 < p.count; k2++) idx.push(k2 + off); }
      off += p.count;
    });
    var out = new T.BufferGeometry();
    out.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    out.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
    out.setAttribute('normal', new T.Float32BufferAttribute(nrm, 3));
    out.setIndex(idx);
    return out;
  }

  /* ---------------------------------------------------------- the bloom
     Every flower file we bought is a PACK: five to eight separate plants
     standing in a row, a metre and a half end to end. The sower measured
     the whole row and scaled that, so one placement was the entire row,
     wrongly sized and carrying up to fifteen thousand triangles. Sown by
     the tens of thousands, the flowers alone were two hundred and thirty
     million triangles, and still too small to see.

     Each plant is now baked to its own sheet at its own true size (the
     width and height in centimetres are in the file name) and sown as a
     crossed card: eight triangles instead of three thousand. That is what
     makes it possible for flowers to be the dominant cover. */
  var FLOWER_CARDS = {
    orange: ['card_fl_orange_2_w24_h7.png', 'card_fl_orange_3_w25_h10.png',
             'card_fl_orange_4_w34_h17.png', 'card_fl_orange_5_w27_h12.png',
             'card_fl_orange_6_w31_h11.png', 'card_fl_orange_7_w24_h11.png'],
    yellow: ['card_fl_yellow_0_w22_h27.png', 'card_fl_yellow_1_w18_h19.png',
             'card_fl_yellow_2_w22_h18.png', 'card_fl_yellow_3_w19_h17.png',
             'card_fl_yellow_4_w11_h15.png'],
    purple: ['card_fl_purple_0_w16_h26.png', 'card_fl_purple_2_w17_h30.png',
             'card_fl_purple_3_w23_h41.png', 'card_fl_purple_4_w11_h21.png',
             'card_fl_purple_5_w26_h40.png'],
    white:  ['card_fl_white_0_w43_h16.png', 'card_fl_white_1_w28_h13.png',
             'card_fl_white_2_w26_h15.png', 'card_fl_white_3_w19_h13.png']
  };
  var FLOWER_KEYS = ['orange', 'yellow', 'purple', 'white'];
  var flCache = {};
  function flowerCard(file) {
    if (flCache[file]) return flCache[file];
    var m = file.match(/_w(\d+)_h(\d+)\.png$/);
    var w = m ? +m[1] / 100 : 0.28, h = m ? +m[2] / 100 : 0.28;
    var c = makeCard('assets/flowers/' + file, w, h, 0xffffff);
    /* Moonlight is weak and blue, and a bloom lit only by it goes black.
       Real flowers hold their colour at night -- pale ones almost shine --
       so the petals carry a little light of their own. Not a glow: just
       enough that the colour survives the dark. */
    c.m.emissive = new T.Color(0xffffff);
    c.m.emissiveMap = c.m.map;
    c.m.emissiveIntensity = 0.30;
    flCache[file] = { g: c.g, m: c.m, w: w, h: h };
    return flCache[file];
  }

  /* Where the ground is deep in growth and where it is thin. Grass does not
     lie at one length over a whole country: it gathers where the water and
     the shade are, in patches tens of metres across, and thins between. */
  function lushField(x, z) {
    var a = W.fbm(x * 0.0125 + 31.7, z * 0.0125 - 12.3, 2);
    var b = W.fbm(x * 0.041 - 5.1, z * 0.041 + 9.7, 2);
    var v = W.sstep(0.32, 0.70, a * 0.70 + b * 0.30);
    /* on the fresh field his painted green IS the lushness: where he lays it
       thick the flowers fill the ground, thinning only a little by the grain */
    if (!W.CLASSIC && W.MAPW) {
      var mg = 0;
      try { mg = W.mapGreen ? W.mapGreen(x, z) : 0; } catch (e) {}
      v = Math.max(v * 0.5, mg * (0.55 + 0.45 * v));
    }
    return v;
  }
  W.lushField = lushField;

  /* ------------------------------------------------------ the blossom row
     GONE, by his order (2026-08-20): "remove the blossom trees wherever they
     are, the line we made". The row of fifteen giants that stood south of the
     town for judging is not built and its models are not fetched - which also
     takes about thirty megabytes out of the second wave. The list stays as an
     empty array because other code still asks for it.
     (The Qasr's own garden still plants blossom; that is a different place
     and a different decision.) */
  var BLOSSOM_ROW = [];
  W.BLOSSOM_ROW = BLOSSOM_ROW;
  /* the flowers wear the land's deeper pigment: darker albedo, and they
     light up under any lamp like everything else does. Called when the
     flowers actually arrive, which is now the second wave. */
  function pigmentFlowers() {
    ['fl_orange', 'fl_yellow', 'fl_purple', 'fl_white'].forEach(function (fk) {
      var mdl = MODELS[fk];
      if (!mdl || mdl.userData.pigmented) return;
      mdl.userData.pigmented = true;
      var seen2 = {};
      mdl.traverse(function (o) {
        if (o.isMesh && o.material && !seen2[o.material.uuid]) {
          seen2[o.material.uuid] = 1;
          var c = o.material.color;
          var isLeaf = c.g > c.r && c.g > c.b;
          c.multiplyScalar(isLeaf ? 0.72 : 0.94);
        }
      });
    });
  }

  /* what grows in one chunk */
  W.scatter = function (W, ci, cj, CH, seg) {
    var out = [];
    var ox = ci * CH, oz = cj * CH;
    var dummy = new T.Object3D();

    var TINT_KEYS = { 'grass_a': 1, 'grass_b': 1, 'plant/tuft_1': 1, 'plant/tuft_2': 1, 'bush_dry': 1 };
    function sowParts(key, count, pick, sizeMin, sizeMax, salt2, around) {
      count = Math.round(count * (W.vegScale || 1));
      var src = vegParts(key);
      if (!src || count <= 0) return;
      var ims = src.parts.map(function (pr) { return new T.InstancedMesh(pr.g, pr.m, count); });
      var n = 0;
      var salt = (key.charCodeAt(0) * 7919 + key.length * 104729 + (salt2 || 0)) | 0;
      for (var i = 0; i < count; i++) {
        var sd = (ci * 73856093) ^ (cj * 19349663) ^ ((i + salt) * 83492791);
        var rx, rz;
        if (around) {
          /* packed round the heart of the drift, thinning to its rim */
          var aa = hashU(sd) * 6.283;
          var rr2 = Math.pow(hashU(sd ^ 0x9e3779b9), 0.55) * around.r;
          rx = around.x + Math.cos(aa) * rr2;
          rz = around.z + Math.sin(aa) * rr2;
        } else {
          rx = ox + hashU(sd) * CH;
          rz = oz + hashU(sd ^ 0x9e3779b9) * CH;
        }
        var h = W.heightAt(rx, rz);
        if (!pick(rx, rz, h, sd)) continue;
        var sc = (sizeMin + hashU(sd ^ 0x85ebca6b) * (sizeMax - sizeMin)) / src.height;
        dummy.position.set(rx, h - 0.05, rz);
        dummy.rotation.set(0, hashU(sd ^ 0xc2b2ae35) * 6.283, 0);
        dummy.scale.set(sc, sc, sc);
        dummy.updateMatrix();
        for (var pi = 0; pi < ims.length; pi++) ims[pi].setMatrixAt(n, dummy.matrix);
        n++;
      }
      if (!n) { ims.forEach(function (im2) { im2.dispose(); }); return; }
      ims.forEach(function (im2) {
        im2.count = n;
        im2.instanceMatrix.needsUpdate = true;
        im2.frustumCulled = false;
        W.scene.add(im2);
        out.push(im2);
      });
    }
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
      if (im.instanceColor) im.instanceColor.needsUpdate = true;
      im.frustumCulled = false;
      W.scene.add(im);
      out.push(im);
    }

    /* the thick carpet of grass */
    if (!cardGeo) {
      /* a blade card is a hand's width and knee high before it is scaled;
         a thumbnail of grass reads as dust from standing height */
      var c1 = makeCard('assets/grass_card.png', 0.62, 0.52, 0xffffff);
      cardGeo = c1.g; cardMat = c1.m;
      var c2 = makeCard('assets/reed_card.png', 0.34, 1.15, 0xd2e0bd);
      reedGeo = c2.g; reedMat = c2.m;
    }
    /* the tuft wears the ground's own colour: dry gold where the land is dry,
       meadow green where it is green, drifting in the same big patches */
    /* the blade sprite is painted FROM the terrain sheet, so the tint only
       repeats the shader's own modulation: green side (0.90,1.0,0.78) with
       the big tone patches, dry side pulled to straw (1.30,1.06,0.60) */
    function landTint(x, z, g, sd) {
      var t = W.sstep(0.44, 0.76, g);
      var tone = 0.74 + 0.52 * W.fbm(x * 0.00072 + 0.37, z * 0.00072 + 0.11, 2);
      var tone2 = 0.62 + 0.55 * W.fbm(x * 0.0172 + 0.2, z * 0.0172 + 0.7, 2);
      var j = 0.92 + hashU((sd ^ 0x51f) | 0) * 0.16;
      var gr = [0.90 * tone2, 1.00 * tone2, 0.78 * tone2];
      var dr = [1.30 * 0.9, 1.06 * 0.9, 0.60 * 0.9];
      /* the ground shader has its own night curve; the cards do not -- this
         lift closes the measured 50% gap between fur and soil */
      var L = 1.42 * tone * j;
      return [
        (dr[0] + (gr[0] - dr[0]) * t) * L,
        (dr[1] + (gr[1] - dr[1]) * t) * L,
        (dr[2] + (gr[2] - dr[2]) * t) * L
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
        /* thin out with the growth, never a hard edge, and thicken where the
           ground is deep in it: a meadow is patchy, not a mown lawn */
        var lfc = lushField(rx, rz);
        if (hashU(sd ^ 0x3d7) > (0.10 + 0.90 * w.g) * (0.42 + 0.80 * lfc)) continue;
        if (W.flatAt(rx, rz) > 0.30 || W.roadAt(rx, rz) > 0.35) continue;
        /* length and width both run with the ground: knee high in the thin
           places, waist high in the deep ones */
        var sc = (sMin + hashU(sd ^ 0x85ebca6b) * (sMax - sMin)) *
                 (0.55 + 0.65 * w.g) * (0.70 + 0.80 * lfc);
        dummy.position.set(rx, h - 0.07, rz);
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
    sowCards(cardGeo, cardMat, Math.round(15000 * (0.40 + cb.grass) * (W.vegScale || 1)), 0.75, 1.70);
    sowReeds(reedGeo, reedMat, Math.round(260 * (W.vegScale || 1)));
    /* THE SUPERWORLD OF FLOWERS: instanced drifts of one colour after
       another across every green chunk, near or far -- one draw per species
       per part per chunk, so the bloom costs almost nothing */
    W.DRIFTS = W.DRIFTS || [];
    for (var fd = 0; fd < FLOWER_KEYS.length; fd++) {
      var fk2 = FLOWER_KEYS[fd], all = FLOWER_CARDS[fk2];
      var d1 = (ci * 48611 + cj * 75377 + fd * 30011) | 0;
      if (hashU(d1 ^ 0x5c3) < 0.16) continue;   /* a few chunks miss a colour */
      /* three of this colour's plants for this chunk, so no two chunks of
         the same bloom are made of exactly the same stems */
      var files = [];
      for (var q = 0; q < 3; q++) {
        files.push(all[Math.floor(hashU(d1 ^ (0x51 + q * 0x9d)) * all.length) % all.length]);
      }
      /* three hearts, each tens of metres across, and a loose wandering */
      var hearts = [];
      for (var dr = 0; dr < 3; dr++) {
        var ds = (d1 ^ ((dr + 1) * 0x9e37)) | 0;
        var ht = { x: ox + hashU(ds) * CH, z: oz + hashU(ds ^ 0x77f) * CH,
                   r: 13 + hashU(ds ^ 0x3e7) * 23 };
        hearts.push(ht);
        W.DRIFTS.push([fk2, Math.round(ht.x), Math.round(ht.z), Math.round(ht.r)]);
      }
      var mats = [[], [], []];
      var N = Math.round(2600 * (W.vegScale || 1));
      for (var i2 = 0; i2 < N; i2++) {
        var sd2 = (ci * 73856093) ^ (cj * 19349663) ^ ((i2 + fd * 7919 + 331) * 83492791);
        var rx2, rz2;
        if (i2 % 8 === 7) {                      /* one in eight wanders free */
          rx2 = ox + hashU(sd2) * CH; rz2 = oz + hashU(sd2 ^ 0x9e3779b9) * CH;
        } else {
          var ht2 = hearts[i2 % 3];
          var aa2 = hashU(sd2) * 6.283;
          var rr2 = Math.pow(hashU(sd2 ^ 0x9e3779b9), 0.58) * ht2.r;
          rx2 = ht2.x + Math.cos(aa2) * rr2; rz2 = ht2.z + Math.sin(aa2) * rr2;
        }
        var h2 = W.heightAt(rx2, rz2);
        if (!lush(rx2, rz2, h2)) continue;
        var lf2 = lushField(rx2, rz2);
        if (hashU(sd2 ^ 0x2b1) > 0.34 + 0.78 * lf2) continue;
        /* true size, then the ground's own generosity on top of it */
        var sc2 = (0.85 + hashU(sd2 ^ 0x85ebca6b) * 0.85) * (0.80 + 0.95 * lf2);
        dummy.position.set(rx2, h2 - 0.03, rz2);
        dummy.rotation.set(0, hashU(sd2 ^ 0xc2b2ae35) * 6.283, 0);
        dummy.scale.set(sc2, sc2, sc2);
        dummy.updateMatrix();
        mats[Math.floor(hashU(sd2 ^ 0x7c1) * 3) % 3].push(dummy.matrix.clone());
      }
      for (var fi = 0; fi < 3; fi++) {
        if (!mats[fi].length) continue;
        var cd = flowerCard(files[fi]);
        var imf = new T.InstancedMesh(cd.g, cd.m, mats[fi].length);
        for (var mi2 = 0; mi2 < mats[fi].length; mi2++) imf.setMatrixAt(mi2, mats[fi][mi2]);
        imf.instanceMatrix.needsUpdate = true;
        imf.frustumCulled = false;
        W.scene.add(imf);
        out.push(imf);
      }
    }

    var near = (seg === undefined) || seg >= 32;
    if (near) {
      sow('grass_a', Math.round(100 * (0.35 + cb.grass)), lush, 0.8, 1.7);
      sow('grass_b', Math.round(112 * (0.3 + cb.grass)), lush, 0.7, 1.5);
      /* flower meadows: a few strong clumps per chunk, each one colour,
         so the bloom reads as a patch of colour from far off */
    }
    sow('bush_dry', Math.round(24 * (1 - cb.grass)), dry, 0.8, 1.7);
    sow('rock_d', Math.round(9 * (0.3 + cb.rock)), stony, 0.8, 2.2);
    sow('rock_small', Math.round(30 * (0.4 + cb.rock)), dry, 0.7, 1.9);
    sow('rock_small', Math.round(16 * (0.3 + cb.rock)), stony, 0.7, 1.9);
    if (near) {
      sow('plant/tuft_1', Math.round(38 * (0.3 + cb.grass)), lush, 0.9, 1.5);
      sow('plant/tuft_2', Math.round(32 * (0.3 + cb.grass)), lush, 0.9, 1.5);
      /* the primitive plants are purged: only photographed-grade cover
         remains -- cards, real tufts, real flowers, real scrub */
      sow('bush_dry', Math.round((10 + 20 * fMask) * (0.3 + cb.grass)), lush, 0.7, 1.3);
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
    /* the fresh field is his blank canvas: palms come from his palm brush,
       never sprinkled over the open plain (the flat plain sits near the
       water table, so wetness alone calls everywhere a shoreline) */
    if (!W.CLASSIC) palmChunk = !!(W.mapPalm && W.mapPalm(ox + CH / 2, oz + CH / 2) > 0.4);
    /* the light forests: big soft patches of woodland out in the country */
    var fMask;
    if (!W.CLASSIC) {
      /* the fresh field grows forests only where he paints them */
      fMask = W.mapForest ? W.mapForest(ox + CH / 2, oz + CH / 2) : 0;
    } else {
      fMask = W.sstep(0.58, 0.74, W.fbm((ox + CH / 2) * 0.00052 + 91.3,
                                        (oz + CH / 2) * 0.00052 - 17.9, 3));
      if (W.mapForest) fMask = Math.max(fMask, W.mapForest(ox + CH / 2, oz + CH / 2));
    }
    if (W.mapPalm && W.mapPalm(ox + CH / 2, oz + CH / 2) > 0.4) palmChunk = true;
    var townD2 = Math.hypot(ox + CH / 2, oz + CH / 2);
    if (townD2 < 210) fMask = 0;                    /* the town keeps its air */
    var forest = !palmChunk && fMask > 0.02;
    var treeN = Math.max(1, Math.round((12 * cb.grass + 4) * (1 + 5.5 * fMask) * (W.vegScale || 1)));
    /* Trees keep company. They come up in stands, thick at the heart and
       thinning at the edge, tens of metres across, with the odd loner out
       on its own -- an even sprinkle over a whole chunk is an orchard grid,
       and reads as one. */
    var treeJobs = [];
    function instanceTrees(jobs) {
      if (!jobs.length) return;
      var byKey = {};
      jobs.forEach(function (j) { (byKey[j.key] = byKey[j.key] || []).push(j); });
      Object.keys(byKey).forEach(function (k2) {
        var src = vegParts(k2);
        if (!src) return;
        var list = byKey[k2];
        var ims = src.parts.map(function (pr) {
          return new T.InstancedMesh(pr.g, pr.m, list.length);
        });
        for (var i3 = 0; i3 < list.length; i3++) {
          var j2 = list[i3];
          /* the tree/* models are placed at true size; the older ones were
             normalised to a height, so they keep that convention */
          var s3 = j2.raw ? j2.sc : (j2.sc / src.height);
          dummy.position.set(j2.x, j2.y, j2.z);
          dummy.rotation.set(0, j2.rot, 0);
          dummy.scale.set(s3, s3, s3);
          dummy.updateMatrix();
          for (var p3 = 0; p3 < ims.length; p3++) ims[p3].setMatrixAt(i3, dummy.matrix);
        }
        ims.forEach(function (im3) {
          im3.name = 'trees:' + k2;              /* so a fault names its kind */
          im3.instanceMatrix.needsUpdate = true;
          /* culling OFF: an InstancedMesh keeps its GEOMETRY's bounding
             sphere, which sits at the model origin -- not where the
             instances stand. Culled on, whole stands of trees appeared and
             vanished with the camera's angle. The chunk system already
             removes them with their chunk. */
          im3.frustumCulled = false;
          W.scene.add(im3);
          out.push(im3);
        });
      });
    }
    var nStand = 1 + Math.floor(rng(ci, cj, 4.4) * 3);
    var STANDS = [];
    for (var s2 = 0; s2 < nStand; s2++) {
      STANDS.push({ x: ox + rng(ci + s2 * 11, cj, 1.7) * CH,
                    z: oz + rng(ci, cj + s2 * 13, 2.9) * CH,
                    r: 9 + rng(ci + s2, cj + s2, 5.1) * 26 });
    }
    for (var t = 0; t < treeN; t++) {
      var tx, tz;
      if (t % 7 === 6) {
        tx = ox + rng(ci + t, cj, 3.9) * CH; tz = oz + rng(ci, cj + t, 8.4) * CH;
      } else {
        var stnd = STANDS[t % STANDS.length];
        var tang = rng(ci + t, cj, 3.9) * 6.283;
        var trr = Math.pow(rng(ci, cj + t, 8.4), 0.62) * stnd.r;
        tx = stnd.x + Math.cos(tang) * trr; tz = stnd.z + Math.sin(tang) * trr;
      }
      var th = W.heightAt(tx, tz);
      var w = W.groundWeights(tx, tz, th);
      if (th < W.WATER_Y + 0.5) continue;
      var key = null, sc = 1;
      var own = rng(tx, tz, 2.7);        /* the Blender-grown trees, true size */
      /* Blossom giants are NEVER sown -- his order. The only ones anywhere
         are the row in front of the city. (A leftover branch here from the
         normalized era was multiplying true-size 20m trees by 38-106: the
         sky-filling slabs and the "massive trees all over the map".) */
      if (palmChunk) {
        if (w.w > 0.24 || !W.CLASSIC) {   /* his painted grove floors are dry land */
          if (own > 0.82) {              /* tamarisk holds the bank with them */
            key = 'tree/tamarisk_' + (1 + Math.floor(rng(tx, tz, 9.9) * 5) % 5);
            sc = 0.9 + rng(tx, tz, 5.5) * 0.5;
          } else {
            key = 'palm'; sc = 8 + rng(tx, tz, 7) * 5;
          }
        }
      } else if (forest ? (w.g > 0.30) : (w.g > 0.55 && own > 0.5)) {
        var TS;
        if (forest && rng(tx, tz, 7.7) > 0.35) {
          /* the forest wall is conifer, as the reference shows */
          TS = ['tree/pine_1', 'tree/pine_2', 'tree/pine_3', 'tree/pine_4', 'tree/pine_5'];
        } else {
          TS = ['tree/olive_1', 'tree/olive_2', 'tree/olive_3', 'tree/olive_4', 'tree/olive_5',
                'tree/plane_1', 'tree/plane_2', 'tree/plane_3', 'tree/plane_4', 'tree/plane_5',
                'tree/fig_1', 'tree/fig_2', 'tree/fig_3', 'tree/fig_4', 'tree/fig_5',
                'tree/cypress_1', 'tree/cypress_2', 'tree/cypress_3', 'tree/cypress_4',
                'tree/cypress_5'];
        }
        key = TS[Math.floor(rng(tx, tz, 3.3) * TS.length) % TS.length];
        sc = 0.9 + rng(tx, tz, 5.5) * 0.5;
      }
      /* The old normalised trees are OUT of the world by his order: tree_anc
         was being stood up at twenty-four to thirty-eight metres, tree_big_a
         and _b at eleven to nineteen, scattered across the whole map. Nothing
         huge grows in the open country any more, and since 2026-08-20 there
         are no blossom giants anywhere in the world either. */
      if (!key || !MODELS[key]) continue;
      /* Trees used to be placed one clone at a time, which is two draw calls
         each. Seven hundred and forty trees was fourteen hundred and eighty
         draw calls on their own -- the single biggest reason the world would
         not hold a frame rate on an integrated chip. They are gathered here
         and drawn per kind instead. Collision stays per tree. */
      treeJobs.push({ key: key, x: tx, y: th - 0.25, z: tz, sc: sc,
                      rot: rng(tx, tz, 9) * 6.283,
                      raw: key.indexOf('tree/') === 0 });
      if (key.indexOf('tree/blossom_') === 0) {
        var br = 0.030 * sc + 0.6;
        W.addBox(tx, th + sc * 0.10, tz, br, sc * 0.10, br, 0);
      } else if (key.indexOf('tree/') === 0) {
        W.addBox(tx, th + 2.2, tz, 0.38, 2.2, 0.38, 0);
      } else {
        W.addBox(tx, th + sc * 0.30, tz, sc * 0.045 + 0.25, sc * 0.30, sc * 0.045 + 0.25, 0);
      }
    }
    instanceTrees(treeJobs);
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
      var c1 = makeCard('assets/grass_card.png', 0.62, 0.52, 0xffffff);
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
      /* The carpet thins towards its rim. Cut off square, it reads from the
         air as a dark disc following the player around the country. */
      var edge = r / LAWN_R;
      if (hashU(sd ^ 0x51f) < edge * edge * 1.2 - 0.20) continue;
      var gx = p.x + Math.cos(a) * r, gz = p.z + Math.sin(a) * r;
      var h = W.heightAt(gx, gz);
      var w = W.groundWeights(gx, gz, h);
      if (h < W.WATER_Y + 0.12 || w.g < 0.20 || w.r > 0.65) continue;
      if (W.flatAt(gx, gz) > 0.30 || W.roadAt(gx, gz) > 0.35) continue;
      var lfl = lushField(gx, gz);
      var sc = (0.60 + hashU(sd ^ 0x85ebca6b) * 0.95) * (0.55 + 0.65 * w.g) * (0.70 + 0.80 * lfl);
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


  /* ------------------------------------------------------------ crunching
     The town is assembled out of about seventeen hundred small meshes: six
     hundred and eighty sprite planes at two triangles each, four hundred and
     seventy boxes at twelve. They cost almost nothing to draw and everything
     to ISSUE -- one draw call apiece, which is what an integrated chip runs
     out of long before it runs out of triangles.

     Everything static is welded into one mesh per material after the world is
     built. Anything that moves, opens, flickers, or is aimed at the player is
     left alone. */
  function crunch() {
    var keep = new Set();
    function protect(o) {
      if (!o) return;
      o.traverse ? o.traverse(function (c) { keep.add(c); }) : keep.add(o);
    }
    doors.forEach(function (d) { protect(d.pivot); protect(d.leaf); });
    fires.forEach(function (f) { protect(f.g || f.mesh || f); });
    /* A LAMP'S GLOW WAS BEING KEPT OUT OF THE WELD FOR NOTHING. A fire moves
       - its sheets run their frames and its embers rise - so it has to stay
       loose. A lamp does not: the flicker is carried by the pooled point
       light, and the smear of light on the sprite is never touched after it
       is made. So a thousand static planes were each costing their own draw
       call. They weld now, and the weld's own cell culling does the LOD far
       better than a distance test could. Measured: 1,411 calls -> see below. */
    /* The small props were kept out of the weld because they are shown and
       hidden by distance to save draw calls. Welding saves far more than the
       toggling ever did, so they go in and the toggle list is emptied. */
    /* only what MOVES stays loose. A fire's sheets run their frames and its
       embers rise, so it is protected; a lamp's glow is a plane that is set
       down once and never touched again. */
    EMIT.forEach(function (e) { if (e.layers) protect(e.g || e.mesh); });

    var groups = new Map();
    var victims = [];
    W.scene.traverse(function (o) {
      if (!o.isMesh || o.isInstancedMesh || o.isSkinnedMesh) return;
      if (keep.has(o)) return;
      if (o.userData && o.userData.noCrunch) return;
      var g = o.geometry;
      if (!g || !g.attributes || !g.attributes.position) return;
      /* only weld what will never move again */
      var moving = false;
      for (var pnt = o; pnt; pnt = pnt.parent) {
        if (keep.has(pnt) || (pnt.userData && pnt.userData.noCrunch)) { moving = true; break; }
      }
      if (moving) return;
      var m = o.material;
      if (Array.isArray(m)) return;
      /* billboards, glows and anything additive live by being re-aimed or
         faded every frame; welded they freeze into dark slabs in the sky */
      if (!(o.userData && o.userData.weldGlow)) {
        if (m.isMeshBasicMaterial || m.transparent || m.blending !== T.NormalBlending) return;
      }
      /* Weld by material AND by where it stands. One batch for the whole
         town is one draw call, but it is never off screen, so all eight and
         a half million triangles are pushed every frame wherever you look.
         Cut into cells, the half of the town behind you is culled. */
      o.updateWorldMatrix(true, false);
      if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
      var wc = o.geometry.boundingSphere.center.clone().applyMatrix4(o.matrixWorld);
      /* THE CELL WAS NEARLY HALF THE TOWN. Welding by 110 m cells means a
         street view holds most of them, so frustum culling never bites and
         eleven million triangles go out every frame. Sixty metres costs a few
         more batches and lets the half of the town behind you drop out. */
      /* MEASURED, THREE WAYS, from the same street with the market standing.
         110 m: 312 batches, 11.5 M triangles, 74 ms.
          60 m: 607 batches,  7.2 M triangles, 70 ms.
          85 m: 524 batches,  6.7 M triangles, 62 ms.
         Then every prop in the town was slimmed and the triangles fell to
         4.3 M - and the frame did not move at all. That settles it: this
         machine is not pushing triangles, it is issuing DRAW CALLS, and the
         cell was making hundreds of them to save triangles that cost nothing.
         So the cell is now bigger than the town: one batch per material, and
         the whole town goes out in a few dozen calls. */
      var CELL = 400;
      var key = m.uuid + '|' + Math.floor(wc.x / CELL) + '_' + Math.floor(wc.z / CELL);
      if (!groups.has(key)) groups.set(key, { mat: m, list: [] });
      groups.get(key).list.push(o);
      victims.push(o);
    });

    var made = 0, removed = 0;
    groups.forEach(function (grp) {
      if (grp.list.length < 3) return;          /* not worth a weld */
      /* THE WELD, MEASURED: this took 22 seconds of the load. It walked every
         vertex of nearly four thousand meshes through accessor calls and
         pushed each number onto a growing plain array. Now it counts first,
         allocates once, and reads the raw typed arrays with the matrix
         multiplied out by hand. Same result, a fraction of the time.

         Every Blender asset carries its shading in COLOR_0 and its material
         says vertexColors, so the colour has to come through too - white
         where a piece never had one, or the batch renders black. */
      var wantCol = !!grp.mat.vertexColors;
      var use = [], total = 0, idxTotal = 0, ok = true;
      for (var i = 0; i < grp.list.length; i++) {
        var o = grp.list[i], g = o.geometry;
        var ap = g.attributes.position;
        if (!ap) { ok = false; break; }
        o.updateWorldMatrix(true, false);
        var me2 = o.matrixWorld.elements, finite = true;
        for (var fe = 0; fe < 16; fe++) if (!isFinite(me2[fe])) { finite = false; break; }
        if (!finite) continue;              /* one bad transform poisons a batch */
        use.push(o);
        total += ap.count;
        idxTotal += g.index ? g.index.count : ap.count;
      }
      if (!ok || !total) return;

      var pos = new Float32Array(total * 3);
      var nrm = new Float32Array(total * 3);
      var uv = new Float32Array(total * 2);
      var col = wantCol ? new Float32Array(total * 3) : null;
      var idx = (total > 65535) ? new Uint32Array(idxTotal) : new Uint16Array(idxTotal);
      var vp = 0, vn = 0, vu = 0, vc = 0, vi = 0, off = 0;

      function readScale(attr) {
        /* a quantised attribute stores ints; getX would divide, raw reads do not */
        if (!attr.normalized) return 1;
        var a = attr.array;
        if (a instanceof Int8Array) return 1 / 127;
        if (a instanceof Uint8Array) return 1 / 255;
        if (a instanceof Int16Array) return 1 / 32767;
        if (a instanceof Uint16Array) return 1 / 65535;
        return 1;
      }

      for (var u = 0; u < use.length; u++) {
        var ob = use[u], geo = ob.geometry;
        var pa = geo.attributes.position, na = geo.attributes.normal;
        var ua = geo.attributes.uv, ca = wantCol ? geo.attributes.color : null;
        var m = ob.matrixWorld.elements;
        var m0 = m[0], m1 = m[1], m2 = m[2], m4 = m[4], m5 = m[5], m6 = m[6],
            m8 = m[8], m9 = m[9], m10 = m[10], m12 = m[12], m13 = m[13], m14 = m[14];
        /* A quantised attribute arrives INTERLEAVED: its numbers live in a
           shared buffer with a stride and an offset, and reading it as a
           plain packed array shreds the mesh into spikes - which is exactly
           what it did the first time. */
        function view(at, fallbackItems) {
          if (!at) return { a: null, o: 0, s: fallbackItems, k: 1 };
          var inter = !!at.isInterleavedBufferAttribute;
          return {
            a: inter ? at.data.array : at.array,
            o: inter ? at.offset : 0,
            s: inter ? at.data.stride : at.itemSize,
            k: readScale(at)
          };
        }
        var P = view(pa, 3), N = view(na, 3), U = view(ua, 2), C = view(ca, 3);
        var pArr = P.a, pOff = P.o, pStr = P.s, pSc = P.k;
        var nArr = N.a, nOff = N.o, nStr = N.s, nSc = N.k;
        var uArr = U.a, uOff = U.o, uStr = U.s, uSc = U.k;
        var cArr = C.a, cOff = C.o, cStr = C.s, cSc = C.k;
        var n = pa.count;
        for (var k = 0; k < n; k++) {
          var pi = pOff + k * pStr;
          var x = pArr[pi] * pSc, y = pArr[pi + 1] * pSc, z = pArr[pi + 2] * pSc;
          pos[vp++] = m0 * x + m4 * y + m8 * z + m12;
          pos[vp++] = m1 * x + m5 * y + m9 * z + m13;
          pos[vp++] = m2 * x + m6 * y + m10 * z + m14;
          if (nArr) {
            var ni = nOff + k * nStr;
            var nx = nArr[ni] * nSc, ny = nArr[ni + 1] * nSc, nz = nArr[ni + 2] * nSc;
            var wx = m0 * nx + m4 * ny + m8 * nz;
            var wy = m1 * nx + m5 * ny + m9 * nz;
            var wz = m2 * nx + m6 * ny + m10 * nz;
            var L = Math.sqrt(wx * wx + wy * wy + wz * wz) || 1;
            nrm[vn++] = wx / L; nrm[vn++] = wy / L; nrm[vn++] = wz / L;
          } else { nrm[vn++] = 0; nrm[vn++] = 1; nrm[vn++] = 0; }
          if (uArr) {
            var ui = uOff + k * uStr;
            uv[vu++] = uArr[ui] * uSc; uv[vu++] = uArr[ui + 1] * uSc;
          } else { vu += 2; }
          if (wantCol) {
            if (cArr) {
              var ci = cOff + k * cStr;
              col[vc++] = cArr[ci] * cSc; col[vc++] = cArr[ci + 1] * cSc; col[vc++] = cArr[ci + 2] * cSc;
            } else { col[vc++] = 1; col[vc++] = 1; col[vc++] = 1; }
          }
        }
        var ix = geo.index;
        if (ix) {
          var iArr = ix.array;
          for (var q = 0; q < ix.count; q++) idx[vi++] = iArr[q] + off;
        } else {
          for (var q2 = 0; q2 < n; q2++) idx[vi++] = q2 + off;
        }
        off += n;
      }
      grp.list = use;
      var merged = new T.BufferGeometry();
      merged.setAttribute('position', new T.BufferAttribute(pos, 3));
      merged.setAttribute('normal', new T.BufferAttribute(nrm, 3));
      merged.setAttribute('uv', new T.BufferAttribute(uv, 2));
      if (wantCol && col) merged.setAttribute('color', new T.BufferAttribute(col, 3));
      merged.setIndex(new T.BufferAttribute(idx, 1));
      merged.computeBoundingSphere();
      var mesh = new T.Mesh(merged, grp.mat);
      mesh.name = 'welded';
      mesh.userData.noCrunch = true;
      mesh.frustumCulled = true;
      W.scene.add(mesh);
      made++;
      grp.list.forEach(function (o) {
        var mw2 = o.matrixWorld.elements, fin2 = true;
        for (var fe2 = 0; fe2 < 16; fe2++) if (!isFinite(mw2[fe2])) { fin2 = false; break; }
        if (!fin2) return;                      /* it was skipped, so it stays */
        if (o.parent) o.parent.remove(o);
        o.geometry.dispose();
        removed++;
      });
    });
    SMALL.length = 0;
    if (W.diag) W.diag('welded ' + removed + ' meshes into ' + made);
    return { made: made, removed: removed };
  }
  W.crunch = crunch;

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
      /* The doors cannot be welded - they swing - so each leaf, rib, band and
         knob is its own draw call, and a town of them was twelve hundred of
         them at once. A closed doorway forty metres off is a dark line: the
         leaf is hidden past that and the doorway reads the same. */
      for (var dI = 0; dI < doors.length; dI++) {
        var dr = doors[dI];
        var ddx = dr.x - cp.x, ddz = dr.z - cp.z;
        var near = (ddx * ddx + ddz * ddz) < 2000;
        if (dr.pivot && dr.pivot.visible !== near) dr.pivot.visible = near;
      }
    }
    for (var l = 0; l < lamps.length; l++) {
      var lp = lamps[l];
      if (lp.d2 > 60000) { lp.g.visible = false; continue; }
      lp.g.visible = true;
      lp.g.lookAt(cp);
      lp.g.material.opacity = 0.5 + 0.16 * lp.lit;
    }
    for (var fy2 = 0; fy2 < FIREFLIES.length; fy2++) {
      var fl2 = FIREFLIES[fy2];
      fl2.s.position.set(
        fl2.x + Math.sin(t * 0.31 + fl2.p1) * 1.35,
        fl2.y + Math.sin(t * 0.22 + fl2.p2) * 0.85,
        fl2.z + Math.cos(t * 0.27 + fl2.p3) * 1.35);
      fl2.s.material.opacity = 0.55 + 0.35 * Math.sin(t * 1.7 + fl2.p1 * 3.0);
    }
    for (var d2 = 0; d2 < doors.length; d2++) {
      var dr = doors[d2];
      var target = dr.open ? (dr.dir || -1) * 1.95 : 0;
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
    /* the levelling and the streets first: everything else is placed at an
       absolute height, but the ground has to be under it */
    try {
      var g = JSON.parse(localStorage.getItem('amirat.layout.ground') || 'null');
      if (g) {
        (g.flats || []).forEach(function (f) { W.addFlat(f[0], f[1], f[2], f[3], f[4]); });
        (g.roads || []).forEach(function (r) { W.addRoad(r[0], r[1], r[2], r[3], r[4]); });
        (g.structs || []).forEach(function (st) {
          try {
            if (st.f === 'palace') buildPalace(st.x, st.z);
            else if (st.f === 'library') buildLibrary(st.x, st.z);
          } catch (e) { if (W.diag) W.diag('rebuild ' + st.f + ': ' + e.message); }
        });
        if (W.touchTerrain) { try { W.touchTerrain(0, 0, 4000); } catch (e) {} }
      }
    } catch (e) {}
    var keys = [];
    list.forEach(function (o) { if (keys.indexOf(o.k) < 0) keys.push(o.k); });
    /* The side files come FIRST now, because a model may bring a garden with
       it: the qasr's trees, flowers, grass and torches are models of their
       own, named in its .fx.json, and nothing can be planted until they have
       been fetched. */
    Promise.all(keys.map(loadCollision)).then(function () {
      var extra = [];
      keys.forEach(function (k) {
        var j = FXJSON[k];
        (j && j.garden || []).forEach(function (gg) {
          if (keys.indexOf(gg.k) < 0 && extra.indexOf(gg.k) < 0) extra.push(gg.k);
        });
      });
      return Promise.all(extra.map(loadCollision)).then(function () { return extra; });
    }).then(function (extra) {
    loadModels(keys.concat(extra), function () {
      var made = 0;
      list.forEach(function (o, idx) {
        var sc = o.s === undefined ? 1 : o.s;
        if (placeBuilt(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, sc)) {
          made++;
          /* doors, torch brackets and props hang off the exported spots */
          dressBuilding(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, sc, idx * 131 + 7);
          spawnModelDoors(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, sc);
          spawnModelFx(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, sc);
          spawnModelExtras(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, sc);
        }
      });
      W.diag('');
      W.LAYOUT_COUNT = made;
      if (!made) W.diag('the layout is empty');
    });
    });
    /* stand the player outside whatever was built */
    var minZ = 0;
    list.forEach(function (o) { if (o.p[2] < minZ) minZ = o.p[2]; });
    W.SPAWN = { x: 0, z: minZ - 40 };
    W.SPAWN_YAW = 0;
  }

  /* ------------------------------------------------ the town, to the editor
     Open index.html?export=1 . The world builds as usual, and when it is
     standing every piece of it is written into the editor's own store, so
     opening editor.html shows the whole town ready to be moved about.

     IT NEVER OVERWRITES WITHOUT KEEPING A COPY: whatever was in the editor
     before is put aside under its own dated key first, and the key is printed.
     A layout is hours of somebody's work and this is one keypress. */
  W.exportTown = function () {
    return PLACED_LOG.slice();
  };
  W.sendTownToEditor = function (download) {
    var list = W.exportTown();
    if (!list.length) { W.diag('nothing to export - the town has not built'); return null; }
    var backup = null;
    try {
      var had = localStorage.getItem('amirat.layout');
      if (had && had.length > 2) {
        backup = 'amirat.layout.before-import';
        localStorage.setItem(backup, had);
      }
      localStorage.setItem('amirat.layout', JSON.stringify(list));
      localStorage.setItem('amirat.layout.ground', JSON.stringify(W.GROUND_LOG));
    } catch (e) {
      W.diag('could not write the editor store: ' + e.message);
      return null;
    }
    if (download !== false) {
      try {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([JSON.stringify(list)],
                 { type: 'application/json' }));
        a.download = 'town-layout.json';
        document.body.appendChild(a); a.click(); a.remove();
      } catch (e) {}
    }
    W.diag('exported ' + list.length + ' pieces (and ' + W.GROUND_LOG.roads.length +
           ' streets) to the editor' +
           (backup ? ' (your old layout is kept under ' + backup + ')' : ''));
    return { count: list.length, backup: backup };
  };

  W.buildAll = function (W) {
    if (W.MAPPREVIEW) {
      /* Walk The Shape: nothing stands, nothing grows. The land, its
         colours, and his water -- that is the whole world, so it opens in a
         breath and the shape is what gets judged. */
      var sp = null;
      try {
        var mj2 = JSON.parse(localStorage.getItem('amirat_worldmap'));
        (mj2 && mj2.sites || []).forEach(function (s2) { if (s2.k === 'spawn') sp = s2; });
      } catch (e) {}
      W.SPAWN = sp ? { x: sp.x, z: sp.z } : { x: 0, z: 260 };
      W.SPAWN_YAW = 0;
      W.SHOTS = {};
      W.scatter = null;
      /* a shape is judged in the light. The game itself stays night-only;
         this is a drawing tool's view, like the editor's raised sun. */
      if (W.setDaylight) W.setDaylight(true);
      W.MODELS_IN = true;
      return;
    }
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
      '14': { x: 0, z: 470, yaw: 0.0, pitch: -0.10, h: 120, fly: true }, /* the oasis from above */
      '15': { x: 800, z: -770, yaw: 3.14159, pitch: -0.04, h: 2.4 }  /* the war test site */
    };

    buildTown();
    buildPalace(36, -34);
    buildLibrary(34, 36);
    buildHouses();
    W.GROUND_LOG.structs.push({ f: 'palace', x: 36, z: -34 },
                              { f: 'library', x: 34, z: 36 });

    W.FETCH_MS = Math.round(performance.now());
    /* the market comes up with the town, not after it: a town whose shops
       arrive late reads as a building site for the first few seconds */
    var FIRST = BUILT.concat(WALL_KIT).concat(ALL_PROPS).concat(W.SOUK_KEYS);
    Promise.all(FIRST.map(loadCollision));
    loadModels(FIRST.concat([
      /* THE FIRST WAVE IS ONLY WHAT STANDS THE TOWN UP. Everything that grows
         out of the ground comes in the second wave and is sown by
         refreshVeg() when it lands - the town is what you are looking at
         while it arrives. */
      'palm', 'lantern', 'mashaf', 'carpet',
      'tree/olive_1', 'tree/cypress_1',
'bound/low']), function () {
        pigmentFlowers();
        /* things that need the models */
        buildCitadel();
        buildSculptedHouses();
        buildSouk();
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
        if (new URLSearchParams(location.search).get('site')) buildTestSite();

        if (W.refreshVeg) W.refreshVeg();
      });
  };
})();
