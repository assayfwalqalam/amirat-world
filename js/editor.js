/* The editor. Free camera, an asset palette, click to place, drag to move.
   Modelled on the way Arma's Eden editor works: you fly where you like, pick a
   thing, put it down, and drag it about until it sits right.

   The layout is a plain list of {k, p, r, s}. The game reads the same list, so
   what you build here is what you walk through. */
(function () {
  'use strict';
  var T, scene, cam, renderer;
  var MODELS = {};           /* key -> loaded scene, cached */
  var LOADING = {};          /* key -> array of callbacks while in flight */
  var PLACED = [];           /* every object in the layout */
  var SEL = [];              /* current selection */
  var nextId = 1;
  var mode = 'select';       /* 'select' | 'place' | 'scatter' */
  var armed = null;          /* asset key waiting to be placed */
  var snapGrid = false, snapGround = true, GRID = 1.0;
  var UNDO = [], REDO = [];
  var loader;
  var ghost = null;          /* the translucent preview under the cursor */

  var keys = {};
  var mouse = { x: 0, y: 0, down: false, btn: 0, dragging: false, look: false,
                sx: 0, sy: 0, moved: 0 };
  var dragPlaneY = 0, dragStart = null, dragVert = false, dragRot = false;

  var STORE = 'amirat.layout';

  /* --------------------------------------------------------------- util */
  function $(id) { return document.getElementById(id); }
  function toast(msg) {
    var t = $('toast');
    t.textContent = msg; t.classList.add('on');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.remove('on'); }, 1400);
  }
  function fmt(n) { return Math.round(n * 100) / 100; }

  /* ------------------------------------------------------------- models */
  function getModel(key, cb) {
    if (MODELS[key]) { cb(MODELS[key]); return; }
    if (LOADING[key]) { LOADING[key].push(cb); return; }
    LOADING[key] = [cb];
    loader.load('assets/models/' + key + '.glb', function (g) {
      g.scene.traverse(function (o) {
        if (o.isMesh) {
          o.castShadow = true; o.receiveShadow = true;
          if (o.material) {
            o.material.envMapIntensity = 0.35;
            if (o.geometry.attributes.color_1) o.geometry.deleteAttribute('color_1');
          }
        }
      });
      MODELS[key] = g.scene;
      var q = LOADING[key]; delete LOADING[key];
      q.forEach(function (f) { f(g.scene); });
    }, undefined, function () {
      var q = LOADING[key] || []; delete LOADING[key];
      W.diag('could not load ' + key);
      q.forEach(function (f) { f(null); });
    });
  }

  /* --------------------------------------------------------------- undo */
  function push(action) {
    UNDO.push(action);
    if (UNDO.length > 200) UNDO.shift();
    REDO.length = 0;
    refreshBar();
  }
  function undo() {
    var a = UNDO.pop();
    if (!a) { toast('nothing to undo'); return; }
    a.undo(); REDO.push(a); refreshBar(); refreshList();
  }
  function redo() {
    var a = REDO.pop();
    if (!a) { toast('nothing to redo'); return; }
    a.redo(); UNDO.push(a); refreshBar(); refreshList();
  }

  /* ------------------------------------------------------------- place */
  function addObject(key, x, y, z, rot, sc, quiet) {
    var rec = { id: nextId++, key: key, x: x, y: y, z: z, rot: rot || 0,
                sc: sc === undefined ? 1 : sc, obj: null };
    PLACED.push(rec);
    getModel(key, function (src) {
      /* Models arrive after the click. If this record was cleared or undone in
         the meantime it must not quietly reappear -- that is what left
         buildings behind after Clear. */
      if (!src || rec.dead || PLACED.indexOf(rec) < 0) return;
      var g = src.clone(true);
      g.position.set(rec.x, rec.y, rec.z);
      g.rotation.y = rec.rot;
      g.scale.setScalar(rec.sc);
      g.userData.rec = rec;
      rec.obj = g;
      scene.add(g);
    });
    if (!quiet) refreshList();
    return rec;
  }
  function removeRecord(rec) {
    rec.dead = true;
    var i = PLACED.indexOf(rec);
    if (i >= 0) PLACED.splice(i, 1);
    if (rec.obj) scene.remove(rec.obj);
    unmark(rec);
    var s = SEL.indexOf(rec);
    if (s >= 0) SEL.splice(s, 1);
  }
  function reAdd(rec) {
    rec.dead = false;
    PLACED.push(rec);
    if (rec.obj) scene.add(rec.obj);
    else getModel(rec.key, function (src) {
      if (!src || rec.dead || PLACED.indexOf(rec) < 0) return;
      var g = src.clone(true);
      g.position.set(rec.x, rec.y, rec.z);
      g.rotation.y = rec.rot; g.scale.setScalar(rec.sc);
      g.userData.rec = rec; rec.obj = g; scene.add(g);
    });
  }
  function applyRec(rec) {
    if (!rec.obj) return;
    rec.obj.position.set(rec.x, rec.y, rec.z);
    rec.obj.rotation.y = rec.rot;
    rec.obj.scale.setScalar(rec.sc);
  }

  /* the way the next thing will face · [ and ] turn it before you put it down */
  var placeRot = 0;
  var placeScale = 1;        /* duplicates keep the source's size */
  var runMode = false;       /* T · each placement offers the next slot beside it */
  var runPrev = null;        /* the last thing placed in this run */
  var runSlot = null;        /* where the next one in the run will stand */

  function runWidth(rec) {
    if (!rec || !rec.obj) return 4;
    var sz = new T.Box3().setFromObject(rec.obj).getSize(new T.Vector3());
    var c = Math.abs(Math.cos(rec.rot)), s2 = Math.abs(Math.sin(rec.rot));
    return Math.max(0.6, sz.x * c + sz.z * s2);
  }

  function placeAt(key, p) {
    var y = snapGround ? W.heightAt(p.x, p.z) : p.y;
    var x = p.x, z = p.z;
    if (snapGrid && !(runMode && runSlot)) { x = Math.round(x / GRID) * GRID; z = Math.round(z / GRID) * GRID; }
    var rec = addObject(key, x, y, z, placeRot, placeScale);
    if (runMode) runPrev = rec;
    push({ undo: function () { removeRecord(rec); refreshList(); },
           redo: function () { reAdd(rec); refreshList(); } });
    /* select it, so the turn and size keys act on what was just placed */
    select(rec, false);
    return rec;
  }

  /* ---------------------------------------------------------- selection */
  function clearSel() { SEL.forEach(unmark); SEL.length = 0; refreshPanel(); refreshList(); updateGizmo(); }
  function mark(rec) {
    if (!rec.obj || rec.marked) return;
    rec.marked = true;
    var box = new T.Box3().setFromObject(rec.obj);
    var h = new T.Box3Helper(box, 0xe0a13c);
    h.userData.helper = true;
    scene.add(h);
    rec.helper = h;
  }
  function unmark(rec) {
    rec.marked = false;
    if (rec.helper) { scene.remove(rec.helper); rec.helper = null; }
  }
  function remark() { SEL.forEach(function (r) { unmark(r); mark(r); }); }
  function select(rec, add) {
    if (!add) { SEL.forEach(unmark); SEL.length = 0; }
    if (rec) {
      var i = SEL.indexOf(rec);
      if (i >= 0) { unmark(rec); SEL.splice(i, 1); }
      else { SEL.push(rec); mark(rec); }
    }
    refreshPanel(); refreshList(); updateGizmo();
    expandGroups();
  }

  /* ------------------------------------------------------------- gizmo
     Handles you grab with the mouse: three arrows to slide along an axis, a
     flat square to slide across the ground, and a ring to turn. Drawn over
     everything and rescaled every frame so it stays the same size on screen
     however far away the thing is. */
  var GIZ = null, gizDrag = null;
  var AXCOL = { x: 0xe0574f, y: 0x7ddc63, z: 0x5b93e8, xz: 0xe0b23c, ry: 0xe0a13c };

  function gizMat(hex) {
    return new T.MeshBasicMaterial({ color: hex, depthTest: false, depthWrite: false,
                                     transparent: true, opacity: 0.95, toneMapped: false });
  }

  function buildGizmo() {
    var g = new T.Group();
    g.renderOrder = 999;
    g.visible = false;

    function arrow(axis, hex) {
      var m = gizMat(hex);
      var sub = new T.Group();
      var shaft = new T.Mesh(new T.CylinderGeometry(0.022, 0.022, 0.78, 8), m);
      shaft.position.y = 0.39;
      var head = new T.Mesh(new T.ConeGeometry(0.075, 0.24, 12), m);
      head.position.y = 0.9;
      var grab = new T.Mesh(new T.CylinderGeometry(0.13, 0.13, 1.05, 6),
                            new T.MeshBasicMaterial({ visible: false }));
      grab.position.y = 0.52;
      sub.add(shaft); sub.add(head); sub.add(grab);
      if (axis === 'x') sub.rotation.z = -Math.PI / 2;
      if (axis === 'z') sub.rotation.x = Math.PI / 2;
      sub.traverse(function (o) {
        o.userData.giz = { mode: 'move', axis: axis };
        o.userData.mat = m;
        o.renderOrder = 999;
      });
      g.add(sub);
      return sub;
    }
    arrow('x', AXCOL.x);
    arrow('y', AXCOL.y);
    arrow('z', AXCOL.z);

    var pm = gizMat(AXCOL.xz);
    pm.side = T.DoubleSide;
    pm.opacity = 0.55;
    var plate = new T.Mesh(new T.PlaneGeometry(0.34, 0.34), pm);
    plate.rotation.x = -Math.PI / 2;
    plate.position.set(0.19, 0.005, 0.19);
    plate.userData.giz = { mode: 'move', axis: 'xz' };
    plate.userData.mat = pm;
    plate.renderOrder = 999;
    g.add(plate);

    var rm = gizMat(AXCOL.ry);
    var ring = new T.Mesh(new T.TorusGeometry(1.05, 0.022, 8, 56), rm);
    ring.rotation.x = Math.PI / 2;
    var rgrab = new T.Mesh(new T.TorusGeometry(1.05, 0.1, 6, 28),
                           new T.MeshBasicMaterial({ visible: false }));
    rgrab.rotation.x = Math.PI / 2;
    ring.userData.giz = { mode: 'turn', axis: 'y' };
    ring.userData.mat = rm;
    rgrab.userData.giz = { mode: 'turn', axis: 'y' };
    rgrab.userData.mat = rm;
    ring.renderOrder = 999; rgrab.renderOrder = 999;
    g.add(ring); g.add(rgrab);

    scene.add(g);
    return g;
  }

  function gizParts() {
    if (!GIZ) return [];
    var out = [];
    GIZ.traverse(function (o) { if (o.isMesh) out.push(o); });
    return out;
  }

  var GRPSEQ = 1;
  function expandGroups() {
    /* a group moves as one: selecting any member selects them all */
    var want = {};
    SEL.forEach(function (r) { if (r.grp) want[r.grp] = 1; });
    PLACED.forEach(function (r) {
      if (r.grp && want[r.grp] && SEL.indexOf(r) < 0) SEL.push(r);
    });
  }
  function groupSel() {
    if (SEL.length < 2) { toast('select at least two things to group'); return; }
    var id = 'g' + (GRPSEQ++) + '_' + Date.now() % 100000;
    SEL.forEach(function (r) { r.grp = id; });
    refreshList(); toast('grouped ' + SEL.length + ' \u00b7 they move as one now');
  }
  function ungroupSel() {
    var n = 0;
    SEL.forEach(function (r) { if (r.grp) { r.grp = null; n++; } });
    refreshList(); toast(n ? 'ungrouped ' + n : 'nothing grouped here');
  }
  function selCentre() {
    if (!SEL.length) return null;
    var c = new T.Vector3();
    SEL.forEach(function (r) { c.x += r.x; c.y += r.y; c.z += r.z; });
    return c.divideScalar(SEL.length);
  }

  function updateGizmo() {
    if (!GIZ) return;
    var c = selCentre();
    if (!c) { GIZ.visible = false; return; }
    GIZ.visible = true;
    GIZ.position.copy(c);
    GIZ.scale.setScalar(Math.max(0.6, cam.position.distanceTo(c) * 0.11));
  }

  function gizHighlight(part) {
    gizParts().forEach(function (o) {
      if (o.userData.mat) o.userData.mat.opacity = (o.userData.giz &&
        o.userData.giz.axis === 'xz') ? 0.55 : 0.95;
    });
    if (part && part.userData.mat) part.userData.mat.opacity = 1.0;
  }

  function pickGizmo(ev) {
    if (!GIZ || !GIZ.visible) return null;
    var r = pointerRay(ev);
    var hits = r.intersectObjects(gizParts(), true);
    for (var i = 0; i < hits.length; i++) {
      var o = hits[i].object;
      while (o && !o.userData.giz) o = o.parent;
      if (o) return { part: o, giz: o.userData.giz, point: hits[i].point };
    }
    return null;
  }

  function axisPoint(ev, origin, dir) {
    var r = pointerRay(ev);
    var ro = r.ray.origin, rd = r.ray.direction;
    var w0 = new T.Vector3().subVectors(origin, ro);
    var a = dir.dot(dir), b = dir.dot(rd), cc = rd.dot(rd);
    var d = dir.dot(w0), e = rd.dot(w0);
    var den = a * cc - b * b;
    if (Math.abs(den) < 1e-6) return null;
    var t = (b * e - cc * d) / den;
    return new T.Vector3().copy(origin).addScaledVector(dir, t);
  }

  function planePoint(ev, y) {
    var r = pointerRay(ev);
    var ro = r.ray.origin, rd = r.ray.direction;
    if (Math.abs(rd.y) < 1e-6) return null;
    var t = (y - ro.y) / rd.y;
    if (t < 0) return null;
    return new T.Vector3(ro.x + rd.x * t, y, ro.z + rd.z * t);
  }

  function beginGizDrag(ev, hit) {
    var c = selCentre();
    var dir = new T.Vector3(hit.giz.axis === 'x' ? 1 : 0,
                            hit.giz.axis === 'y' ? 1 : 0,
                            hit.giz.axis === 'z' ? 1 : 0);
    var start = null, ang0 = 0;
    if (hit.giz.mode === 'move' && hit.giz.axis !== 'xz') {
      start = axisPoint(ev, c, dir);
    } else if (hit.giz.mode === 'move') {
      start = planePoint(ev, c.y);
    } else {
      var pp = planePoint(ev, c.y);
      if (pp) ang0 = Math.atan2(pp.z - c.z, pp.x - c.x);
    }
    gizDrag = {
      giz: hit.giz, dir: dir, centre: c, start: start, ang0: ang0,
      recs: SEL.map(function (r) { return { r: r, x: r.x, y: r.y, z: r.z, rot: r.rot }; })
    };
  }

  function moveGizDrag(ev) {
    if (!gizDrag) return;
    var g = gizDrag;
    if (g.giz.mode === 'turn') {
      var pp = planePoint(ev, g.centre.y);
      if (!pp) return;
      var ang = Math.atan2(pp.z - g.centre.z, pp.x - g.centre.x);
      var d = -(ang - g.ang0);
      g.recs.forEach(function (s) {
        s.r.rot = s.rot + d;
        if (g.recs.length > 1) {
          var dx = s.x - g.centre.x, dz = s.z - g.centre.z;
          s.r.x = g.centre.x + dx * Math.cos(d) - dz * Math.sin(d);
          s.r.z = g.centre.z + dx * Math.sin(d) + dz * Math.cos(d);
        }
        applyRec(s.r);
      });
      $('ry').value = Math.round(((g.recs[0].r.rot * 180 / Math.PI) % 360 + 360) % 360);
    } else if (g.giz.axis === 'xz') {
      var pp2 = planePoint(ev, g.centre.y);
      if (!pp2 || !g.start) return;
      var dx2 = pp2.x - g.start.x, dz2 = pp2.z - g.start.z;
      g.recs.forEach(function (s) {
        var nx = s.x + dx2, nz = s.z + dz2;
        if (snapGrid) { nx = Math.round(nx / GRID) * GRID; nz = Math.round(nz / GRID) * GRID; }
        s.r.x = nx; s.r.z = nz;
        if (snapGround) s.r.y = W.heightAt(nx, nz);
        applyRec(s.r);
      });
    } else {
      var now = axisPoint(ev, g.centre, g.dir);
      if (!now || !g.start) return;
      var d3 = new T.Vector3().subVectors(now, g.start);
      g.recs.forEach(function (s) {
        var nx = s.x + d3.x * g.dir.x, ny = s.y + d3.y * g.dir.y, nz = s.z + d3.z * g.dir.z;
        if (snapGrid && g.dir.y === 0) {
          nx = Math.round(nx / GRID) * GRID; nz = Math.round(nz / GRID) * GRID;
        }
        s.r.x = nx; s.r.y = ny; s.r.z = nz;
        applyRec(s.r);
      });
    }
    remark(); updateGizmo(); refreshPanel();
  }

  function endGizDrag() {
    if (!gizDrag) return;
    var before = gizDrag.recs;
    var after = before.map(function (b) {
      return { r: b.r, x: b.r.x, y: b.r.y, z: b.r.z, rot: b.r.rot };
    });
    var moved = after.some(function (a, i) {
      return a.x !== before[i].x || a.y !== before[i].y ||
             a.z !== before[i].z || a.rot !== before[i].rot;
    });
    gizDrag = null;
    if (!moved) return;
    push({
      undo: function () {
        before.forEach(function (b) { b.r.x = b.x; b.r.y = b.y; b.r.z = b.z; b.r.rot = b.rot; applyRec(b.r); });
        remark(); updateGizmo(); refreshPanel();
      },
      redo: function () {
        after.forEach(function (a) { a.r.x = a.x; a.r.y = a.y; a.r.z = a.z; a.r.rot = a.rot; applyRec(a.r); });
        remark(); updateGizmo(); refreshPanel();
      }
    });
  }

  /* --------------------------------------------------------- the land
     His land modifier: paint the ground itself. A local grid rides over the
     world's own terrain (world.js samples it inside heightAt); the brushes
     raise, lower, smooth, flatten, wet and dry it; every stroke rebuilds
     only the chunks it touched, and the whole grid saves with the town. */
  var LAND = null, landBrush = 'raise', landRad = 18, landStr = 6;
  var landStroke = null, landDirty = false;
  function landInit() {
    if (LAND) return;
    var raw = null;
    try { raw = JSON.parse(localStorage.getItem('amirat.layout.land')); } catch (e) {}
    if (raw && raw.n && raw.elev && raw.elev.length === raw.n * raw.n) {
      LAND = { n: raw.n, size: raw.size,
               elev: new Float32Array(raw.elev),
               water: new Float32Array(raw.water || raw.n * raw.n) };
    } else {
      LAND = { n: 128, size: 1200,
               elev: new Float32Array(128 * 128),
               water: new Float32Array(128 * 128) };
    }
    W.setLandPatch(LAND);
  }
  function landSave() {
    if (!LAND || !landDirty) return;
    try {
      localStorage.setItem('amirat.layout.land', JSON.stringify({
        n: LAND.n, size: LAND.size,
        elev: Array.from(LAND.elev, function (v) { return Math.round(v * 100) / 100; }),
        water: Array.from(LAND.water, function (v) { return Math.round(v * 100) / 100; })
      }));
      landDirty = false;
    } catch (e) { toast('the land would not save: ' + e.message); }
  }
  function landStamp(x, z) {
    if (!LAND) return;
    var n = LAND.n, hs = LAND.size / 2, cell = LAND.size / (n - 1);
    var gx0 = Math.max(0, Math.floor((x - landRad + hs) / cell));
    var gx1 = Math.min(n - 1, Math.ceil((x + landRad + hs) / cell));
    var gz0 = Math.max(0, Math.floor((z - landRad + hs) / cell));
    var gz1 = Math.min(n - 1, Math.ceil((z + landRad + hs) / cell));
    var k = landStr * 0.05;
    for (var gz = gz0; gz <= gz1; gz++) {
      for (var gx = gx0; gx <= gx1; gx++) {
        var wx = gx * cell - hs, wz = gz * cell - hs;
        var d = Math.hypot(wx - x, wz - z);
        if (d > landRad) continue;
        var fall = Math.pow(1 - d / landRad, 1.6);
        var i = gz * n + gx;
        if (landBrush === 'raise') LAND.elev[i] += k * fall * 3.2;
        else if (landBrush === 'lower') LAND.elev[i] -= k * fall * 3.2;
        else if (landBrush === 'flat') LAND.elev[i] *= Math.max(0, 1 - fall * 0.35);
        else if (landBrush === 'water') LAND.water[i] = Math.min(4, LAND.water[i] + k * fall * 2.0);
        else if (landBrush === 'dry') LAND.water[i] = Math.max(0, LAND.water[i] - k * fall * 2.6);
        else if (landBrush === 'smooth') {
          var sum = 0, cnt = 0;
          for (var oz = -1; oz <= 1; oz++) {
            for (var ox = -1; ox <= 1; ox++) {
              var j = (gz + oz) * n + (gx + ox);
              if (j >= 0 && j < n * n) { sum += LAND.elev[j]; cnt++; }
            }
          }
          LAND.elev[i] += (sum / cnt - LAND.elev[i]) * fall * 0.5;
        }
      }
    }
    landDirty = true;
    W.touchTerrain(x, z, landRad + cell * 2);
  }

  /* ---------------------------------------------------------- raycasting */
  var rc;
  function pointerRay(ev) {
    var nx = (ev.clientX / innerWidth) * 2 - 1;
    var ny = -(ev.clientY / innerHeight) * 2 + 1;
    rc.setFromCamera({ x: nx, y: ny }, cam);
    return rc;
  }
  function pickObject(ev) {
    var r = pointerRay(ev);
    var list = [];
    PLACED.forEach(function (p) { if (p.obj) list.push(p.obj); });
    var hits = r.intersectObjects(list, true);
    for (var i = 0; i < hits.length; i++) {
      var o = hits[i].object;
      if (o.userData.giz) continue;
      while (o && !o.userData.rec) o = o.parent;
      if (o) return { rec: o.userData.rec, point: hits[i].point };
    }
    return null;
  }
  function placePoint(ev) {
    /* His order: things go where you point them - on a roof, a wall top, a
       terrace - not only on the ground. A placed model hit wins; the ground
       is the fallback. */
    var hit = pickObject(ev);
    var g = groundPoint(ev);
    if (hit && (!g || pointerRay(ev).ray.origin.distanceTo(hit.point) <
                      pointerRay(ev).ray.origin.distanceTo(g))) {
      return new T.Vector3(hit.point.x, hit.point.y, hit.point.z);
    }
    return g;
  }
  function groundPoint(ev) {
    /* march the ray until it drops below the heightfield · works on any slope */
    var r = pointerRay(ev);
    var o = r.ray.origin, d = r.ray.direction;
    var t = 0.5, prev = o.y - W.heightAt(o.x, o.z);
    for (var i = 0; i < 900; i++) {
      var x = o.x + d.x * t, y = o.y + d.y * t, z = o.z + d.z * t;
      var diff = y - W.heightAt(x, z);
      if (diff <= 0 && prev > 0) {
        return new T.Vector3(x, W.heightAt(x, z), z);
      }
      prev = diff;
      t += Math.max(0.5, t * 0.03);
      if (t > 4000) break;
    }
    return null;
  }

  /* ---------------------------------------------------------------- UI */
  function buildTree(manifest) {
    var tree = $('tree');
    tree.innerHTML = '';
    manifest.groups.forEach(function (g, gi) {
      var d = document.createElement('div');
      d.className = 'grp' + (gi === 0 ? ' open' : '');
      var h = document.createElement('div');
      h.className = 'gh';
      h.textContent = g.name + '  (' + g.items.length + ')';
      h.onclick = function () { d.classList.toggle('open'); };
      d.appendChild(h);
      var box = document.createElement('div');
      box.className = 'items';
      g.items.forEach(function (it) {
        var e = document.createElement('div');
        e.className = 'item';
        e.textContent = it.n;
        e.dataset.key = it.k;
        e.dataset.search = (it.n + ' ' + it.k).toLowerCase();
        e.onclick = function () {
          document.querySelectorAll('.item.sel').forEach(function (q) { q.classList.remove('sel'); });
          e.classList.add('sel');
          armed = it.k;
          placeScale = 1;
          runPrev = null; runSlot = null;
          setMode('place');
          makeGhost(it.k);
          toast(runMode ? 'placing ' + it.n + ' · row on (T)' : 'placing ' + it.n);
        };
        box.appendChild(e);
      });
      d.appendChild(box);
      tree.appendChild(d);
    });
  }

  function makeGhost(key) {
    if (ghost) { scene.remove(ghost); ghost = null; }
    getModel(key, function (src) {
      if (!src || armed !== key) return;
      var g = src.clone(true);
      g.traverse(function (o) {
        if (o.isMesh) {
          o.castShadow = false; o.receiveShadow = false;
          o.material = o.material.clone();
          o.material.transparent = true;
          o.material.opacity = 0.55;
          o.material.depthWrite = false;
        }
      });
      g.visible = false;
      ghost = g;
      scene.add(g);
    });
  }

  function setMode(m) {
    mode = m;
    $('mSelect').classList.toggle('on', m === 'select');
    $('mPlace').classList.toggle('on', m === 'place');
    var sb = $('mScatter'); if (sb) sb.classList.toggle('on', m === 'scatter');
    var lb = $('mLand'); if (lb) lb.classList.toggle('on', m === 'land');
    var lp = $('landPanel'); if (lp) lp.style.display = m === 'land' ? 'block' : 'none';
    if (m === 'select' && ghost) { ghost.visible = false; }
  }

  /* ------------------------------------------------------------- scatter
     Placing a forest one tree at a time is not work anyone should do. A
     scatter drops a whole CLUMP in one click: a chosen radius, a wanted
     count, a minimum spacing so nothing grows through anything else, a size
     range, and a mix of assets so a stand is not one tree stamped over and
     over. It thins toward the rim, the way a real thicket does. */
  var MIX = [];
  function mixLabel() {
    var el = $('bmix'); if (!el) return;
    el.textContent = MIX.length ? ('mix: ' + MIX.join(', ')) : 'mix empty · uses the chosen asset';
  }
  function num(id, dflt) {
    var el = $(id); if (!el) return dflt;
    var v = parseFloat(el.value);
    return isFinite(v) ? v : dflt;
  }
  function scatterAt(p) {
    var keys = ($('bMix') && $('bMix').checked && MIX.length) ? MIX.slice() : (armed ? [armed] : []);
    if (!keys.length) { toast('pick an asset, or add some to the mix'); return; }
    var R = Math.max(1, num('bR', 16)), N = Math.max(1, Math.round(num('bN', 14)));
    var gap = Math.max(0, num('bGap', 2.6));
    var sMin = num('bSmin', 0.85), sMax = num('bSmax', 1.35);
    var edge = Math.min(0.95, Math.max(0, num('bEdge', 0.55)));
    var turn = !$('bRot') || $('bRot').checked;
    var made = [], tries = 0;
    while (made.length < N && tries < N * 60) {
      tries++;
      var a = Math.random() * 6.283;
      /* pow > 0.5 packs the middle and thins the rim */
      var rr = Math.pow(Math.random(), 0.5 + edge) * R;
      var x = p.x + Math.cos(a) * rr, z = p.z + Math.sin(a) * rr;
      var ok = true;
      for (var i = 0; i < made.length; i++) {
        var dx = made[i].x - x, dz = made[i].z - z;
        if (dx * dx + dz * dz < gap * gap) { ok = false; break; }
      }
      if (!ok) continue;
      var key = keys[(Math.random() * keys.length) | 0];
      var y = W.heightAt(x, z);
      var sc = sMin + Math.random() * Math.max(0, sMax - sMin);
      made.push(addObject(key, x, y, z, turn ? Math.random() * 6.283 : placeRot, sc));
    }
    if (!made.length) { toast('nothing fitted · widen the radius or close the spacing'); return; }
    push({ undo: function () { made.forEach(removeRecord); refreshList(); },
           redo: function () { made.forEach(reAdd); refreshList(); } });
    refreshList();
    toast('scattered ' + made.length);
  }

  function refreshBar() {
    $('undo').textContent = 'Undo' + (UNDO.length ? ' (' + UNDO.length + ')' : '');
    $('redo').textContent = 'Redo' + (REDO.length ? ' (' + REDO.length + ')' : '');
  }

  function refreshPanel() {
    var one = SEL.length === 1 ? SEL[0] : null;
    $('selname').textContent = SEL.length === 0 ? 'nothing selected'
      : (SEL.length > 1 ? SEL.length + ' selected' : one.key);
    ['px', 'py', 'pz', 'ry', 'sc'].forEach(function (i) { $(i).disabled = !one; });
    if (!one) { ['px', 'py', 'pz', 'ry', 'sc'].forEach(function (i) { $(i).value = ''; }); return; }
    $('px').value = fmt(one.x); $('py').value = fmt(one.y); $('pz').value = fmt(one.z);
    $('ry').value = Math.round(one.rot * 180 / Math.PI);
    $('sc').value = fmt(one.sc);
  }

  var listAnchor = null;
  function refreshList() {
    var box = $('objs');
    box.innerHTML = '';
    var n = Math.min(PLACED.length, 400);
    for (var i = PLACED.length - 1; i >= PLACED.length - n; i--) {
      (function (rec) {
        var e = document.createElement('div');
        e.className = 'o' + (SEL.indexOf(rec) >= 0 ? ' sel' : '')
                    + (rec.grp ? ' grp' : '');
        e.textContent = (rec.grp ? '\u29c9 ' : '') + rec.key;
        e.onclick = function (ev) {
          if (ev.ctrlKey && listAnchor && listAnchor !== rec &&
              PLACED.indexOf(listAnchor) >= 0) {
            /* his range: hold control, click above or below - everything
               between joins the selection, both ends included */
            var i0 = PLACED.indexOf(listAnchor), i1 = PLACED.indexOf(rec);
            var lo = Math.min(i0, i1), hi = Math.max(i0, i1);
            for (var k = lo; k <= hi; k++) {
              if (SEL.indexOf(PLACED[k]) < 0) SEL.push(PLACED[k]);
            }
            expandGroups();
            remark(); updateGizmo(); refreshPanel(); refreshList();
          } else {
            select(rec, ev.shiftKey);
            listAnchor = rec;
            focusOn(rec);
          }
        };
        box.appendChild(e);
      })(PLACED[i]);
    }
    $('stat').textContent = PLACED.length + ' objects';
  }

  function focusOn(rec) {
    var c = W.camState();
    var dx = c.x - rec.x, dz = c.z - rec.z;
    var d = Math.hypot(dx, dz);
    if (d > 60 || d < 4) {
      W.camState({ x: rec.x + 18, y: rec.y + 12, z: rec.z + 18 });
    }
  }

  /* ------------------------------------------------------- save and load */
  function serialise() {
    return PLACED.map(function (p) {
      var o2 = { k: p.key, p: [fmt(p.x), fmt(p.y), fmt(p.z)], r: fmt(p.rot), s: fmt(p.sc) };
      if (p.grp) o2.g = p.grp;
      return o2;
    });
  }
  function loadLayout(list, quiet) {
    PLACED.slice().forEach(removeRecord);
    SEL.length = 0;
    list.forEach(function (o) {
      var r2 = addObject(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, o.s === undefined ? 1 : o.s, true);
      if (r2 && o.g) r2.grp = o.g;
    });
    refreshList(); refreshPanel();
    if (!quiet) toast('loaded ' + list.length + ' objects');
  }
  function save() {
    try {
      localStorage.setItem(STORE, JSON.stringify(serialise()));
      toast('saved ' + PLACED.length + ' objects');
    } catch (e) { toast('could not save: ' + e.message); }
  }
  function loadSaved(quiet) {
    try {
      var raw = localStorage.getItem(STORE);
      if (!raw) { if (!quiet) toast('nothing saved yet'); return false; }
      loadLayout(JSON.parse(raw), quiet);
      return true;
    } catch (e) { toast('could not load: ' + e.message); return false; }
  }

  /* ------------------------------------------------------------ camera */
  var camVel = new (function () {})();
  function editorStep(dt) {
    if (!document.hasFocus()) keys = {};
    updateGizmo();
    var c = W.camState();
    var sp = keys['ShiftLeft'] || keys['ShiftRight'] ? 78 : (keys['ControlLeft'] ? 6 : 24);
    var fx = Math.sin(c.yaw), fz = Math.cos(c.yaw);
    var f = new T.Vector3(-fx, Math.sin(c.pitch), -fz).normalize();
    var r = new T.Vector3(-f.z, 0, f.x).normalize();
    var wish = new T.Vector3();
    if (keys['KeyW']) wish.add(f);
    if (keys['KeyS']) wish.sub(f);
    if (keys['KeyD']) wish.add(r);
    if (keys['KeyA']) wish.sub(r);
    if (keys['KeyE'] || keys['Space']) wish.y += 1;
    if (keys['KeyQ']) wish.y -= 1;
    if (wish.lengthSq() > 0) {
      wish.normalize().multiplyScalar(sp * dt);
      W.camState({ x: c.x + wish.x, y: c.y + wish.y, z: c.z + wish.z });
    }
  }
  W.editorStep = editorStep;

  /* -------------------------------------------------------------- input */
  function bindInput() {
    var cv = renderer.domElement;

    /* Every one of these clears the key state. A keyup that lands somewhere
       the editor is not listening -- a text field, another window, a menu --
       used to leave the key held down, and the camera slid off on its own. */
    function releaseAll() { keys = {}; }
    addEventListener('blur', releaseAll);
    addEventListener('focus', releaseAll);
    document.addEventListener('visibilitychange', releaseAll);
    document.addEventListener('pointerdown', function (e) {
      if (e.target && e.target !== renderer.domElement) releaseAll();
    }, true);

    addEventListener('keydown', function (e) {
      if (/^(INPUT|TEXTAREA)$/.test((e.target.tagName || ''))) { releaseAll(); return; }
      keys[e.code] = true;
      var ctrl = e.ctrlKey || e.metaKey;
      if (ctrl && e.code === 'KeyZ') { e.preventDefault(); undo(); }
      else if (ctrl && (e.code === 'KeyY' || (e.shiftKey && e.code === 'KeyZ'))) { e.preventDefault(); redo(); }
      else if (ctrl && e.code === 'KeyD') { e.preventDefault(); duplicate(); }
      else if (ctrl && e.code === 'KeyS') { e.preventDefault(); save(); }
      else if (e.code === 'Delete' || e.code === 'Backspace') { e.preventDefault(); del(); }
      else if (e.code === 'Escape') { armed = null; runPrev = null; runSlot = null; setMode('select'); clearSel(); }
      else if (e.code === 'KeyT') {
        runMode = !runMode;
        if (!runMode) { runPrev = null; runSlot = null; }
        else if (SEL.length === 1) runPrev = SEL[0];
        toast(runMode ? 'row placing on · next one lands beside the last' : 'row placing off');
      }
      else if (e.code === 'KeyG') { snapGrid = !snapGrid; refreshSnap(); }
      else if (e.code === 'KeyR') { dragRot = true; }
      else if (e.code === 'BracketLeft') { turn(-Math.PI / 12); }
      else if (e.code === 'BracketRight') { turn(Math.PI / 12); }
      else if (e.code === 'Equal' || e.code === 'NumpadAdd') { nudgeScale(1.08); }
      else if (e.code === 'Minus' || e.code === 'NumpadSubtract') { nudgeScale(1 / 1.08); }
      W.wake();
    });
    addEventListener('keyup', function (e) {
      keys[e.code] = false;
      if (e.code === 'KeyR') dragRot = false;
    });

    cv.addEventListener('contextmenu', function (e) { e.preventDefault(); });

    cv.addEventListener('pointerdown', function (e) {
      cv.setPointerCapture(e.pointerId);
      mouse.down = true; mouse.btn = e.button;
      mouse.sx = e.clientX; mouse.sy = e.clientY; mouse.moved = 0;
      mouse.look = (e.button === 2);
      dragVert = keys['KeyZ'];
      if (e.button === 0) {
        var gh = pickGizmo(e);
        if (gh) { beginGizDrag(e, gh); gizHighlight(gh.part); return; }
      }
      if (e.button === 0 && mode === 'land') {
        landInit();
        var lg = groundPoint(e);
        if (lg) { landStroke = { t: 0 }; landStamp(lg.x, lg.z); }
        return;
      }
      if (e.button === 0 && mode === 'select') {
        var hit = pickObject(e);
        if (hit) {
          if (SEL.indexOf(hit.rec) < 0) select(hit.rec, e.ctrlKey || e.shiftKey);
          expandGroups();
          dragStart = {
            point: hit.point.clone(),
            recs: SEL.map(function (r) { return { r: r, x: r.x, y: r.y, z: r.z, rot: r.rot }; })
          };
          dragPlaneY = hit.point.y;
        } else if (!e.ctrlKey && !e.shiftKey) {
          clearSel();
        }
      }
      W.wake();
    });

    cv.addEventListener('pointermove', function (e) {
      mouse.x = e.clientX; mouse.y = e.clientY;
      mouse.moved += Math.abs(e.movementX) + Math.abs(e.movementY);
      if (mouse.look && mouse.down) {
        var c = W.camState();
        W.camState({
          yaw: c.yaw - e.movementX * 0.0026,
          pitch: Math.max(-1.5, Math.min(1.5, c.pitch - e.movementY * 0.0026))
        });
        W.wake();
        return;
      }
      if (gizDrag) { moveGizDrag(e); return; }
      if (!mouse.down) {
        var hov = pickGizmo(e);
        gizHighlight(hov ? hov.part : null);
        if (hov) { renderer.domElement.style.cursor = 'move'; }
        else { renderer.domElement.style.cursor = ''; }
      }
      if (mode === 'place' && ghost) {
        var g = placePoint(e);
        if (g) {
          if (runMode && runPrev && runPrev.obj) {
            /* the next slot butts against the last piece; the cursor only
               chooses which end of it to grow from */
            var wRun = runWidth(runPrev);
            var dx = Math.cos(placeRot) * wRun, dz = -Math.sin(placeRot) * wRun;
            var aX = runPrev.x + dx, aZ = runPrev.z + dz;
            var bX = runPrev.x - dx, bZ = runPrev.z - dz;
            var useA = (g.x - aX) * (g.x - aX) + (g.z - aZ) * (g.z - aZ) <=
                       (g.x - bX) * (g.x - bX) + (g.z - bZ) * (g.z - bZ);
            runSlot = { x: useA ? aX : bX, z: useA ? aZ : bZ };
            runSlot.y = snapGround ? W.heightAt(runSlot.x, runSlot.z) : runPrev.y;
            ghost.position.set(runSlot.x, runSlot.y, runSlot.z);
          } else {
            runSlot = null;
            if (snapGrid) { g.x = Math.round(g.x / GRID) * GRID; g.z = Math.round(g.z / GRID) * GRID; }
            ghost.position.set(g.x, g.y, g.z);
          }
          ghost.rotation.y = placeRot;
          ghost.visible = true;
        } else ghost.visible = false;
        W.wake();
      }
      if (mouse.down && mouse.btn === 0 && dragStart && SEL.length) {
        dragSelection(e);
        W.wake();
      }
      if (mouse.down && mouse.btn === 0 && mode === 'land' && landStroke) {
        var lg2 = groundPoint(e);
        if (lg2) { landStamp(lg2.x, lg2.z); W.wake(); }
      }
    });

    cv.addEventListener('pointerup', function (e) {
      cv.releasePointerCapture(e.pointerId);
      var wasDrag = mouse.moved > 6;
      mouse.down = false; mouse.look = false;
      if (landStroke) { landStroke = null; landSave(); }
      if (gizDrag) { endGizDrag(); gizHighlight(null); return; }
      if (e.button === 0 && mode === 'place' && armed && !wasDrag) {
        var g = (runMode && runSlot) ? runSlot : placePoint(e);
        if (g) placeAt(armed, g);
      }
      if (e.button === 0 && mode === 'scatter' && !wasDrag) {
        var gs = groundPoint(e);
        if (gs) scatterAt(gs);
      }
      if (dragStart && wasDrag) commitDrag();
      dragStart = null;
    });

    cv.addEventListener('wheel', function (e) {
      e.preventDefault();
      var c = W.camState();
      var f = new T.Vector3(-Math.sin(c.yaw), Math.sin(c.pitch), -Math.cos(c.yaw)).normalize();
      var k = (e.deltaY < 0 ? 1 : -1) * (e.shiftKey ? 22 : 7);
      W.camState({ x: c.x + f.x * k, y: c.y + f.y * k, z: c.z + f.z * k });
      W.wake();
    }, { passive: false });
  }

  function dragSelection(e) {
    if (dragRot) {
      var d = (e.clientX - mouse.sx) * 0.012;
      dragStart.recs.forEach(function (s) { s.r.rot = s.rot + d; applyRec(s.r); });
      remark(); refreshPanel();
      return;
    }
    if (dragVert || keys['KeyZ']) {
      var dy = -(e.clientY - mouse.sy) * 0.06;
      dragStart.recs.forEach(function (s) { s.r.y = s.y + dy; applyRec(s.r); });
      remark(); refreshPanel();
      return;
    }
    var g = groundPoint(e);
    if (!g) return;
    var dx = g.x - dragStart.point.x, dz = g.z - dragStart.point.z;
    dragStart.recs.forEach(function (s) {
      var nx = s.x + dx, nz = s.z + dz;
      if (snapGrid) { nx = Math.round(nx / GRID) * GRID; nz = Math.round(nz / GRID) * GRID; }
      s.r.x = nx; s.r.z = nz;
      if (snapGround) s.r.y = W.heightAt(nx, nz);
      applyRec(s.r);
    });
    remark(); refreshPanel();
  }

  function commitDrag() {
    var before = dragStart.recs.map(function (s) {
      return { r: s.r, x: s.x, y: s.y, z: s.z, rot: s.rot };
    });
    var after = before.map(function (b) {
      return { r: b.r, x: b.r.x, y: b.r.y, z: b.r.z, rot: b.r.rot };
    });
    var moved = after.some(function (a, i) {
      return a.x !== before[i].x || a.y !== before[i].y || a.z !== before[i].z || a.rot !== before[i].rot;
    });
    if (!moved) return;
    push({
      undo: function () { before.forEach(function (b) { b.r.x = b.x; b.r.y = b.y; b.r.z = b.z; b.r.rot = b.rot; applyRec(b.r); }); remark(); refreshPanel(); },
      redo: function () { after.forEach(function (a) { a.r.x = a.x; a.r.y = a.y; a.r.z = a.z; a.r.rot = a.rot; applyRec(a.r); }); remark(); refreshPanel(); }
    });
  }

  function turn(d) {
    if (mode === 'place' && armed && !SEL.length) {
      placeRot += d;
      if (ghost) ghost.rotation.y = placeRot;
      toast('facing ' + Math.round(((placeRot * 180 / Math.PI) % 360 + 360) % 360) + '°');
      W.wake();
      return;
    }
    nudgeRot(d);
  }

  function nudgeRot(d) {
    if (!SEL.length) { toast('select something first'); return; }
    var recs = SEL.slice(), before = recs.map(function (r) { return r.rot; });
    recs.forEach(function (r) { r.rot += d; applyRec(r); });
    var after = recs.map(function (r) { return r.rot; });
    push({ undo: function () { recs.forEach(function (r, i) { r.rot = before[i]; applyRec(r); }); remark(); },
           redo: function () { recs.forEach(function (r, i) { r.rot = after[i]; applyRec(r); }); remark(); } });
    remark(); refreshPanel();
    toast('turned to ' + Math.round(((recs[0].rot * 180 / Math.PI) % 360 + 360) % 360) + '°');
  }
  function nudgeScale(k) {
    if (!SEL.length) return;
    var recs = SEL.slice(), before = recs.map(function (r) { return r.sc; });
    recs.forEach(function (r) { r.sc = Math.max(0.05, r.sc * k); applyRec(r); });
    var after = recs.map(function (r) { return r.sc; });
    push({ undo: function () { recs.forEach(function (r, i) { r.sc = before[i]; applyRec(r); }); remark(); },
           redo: function () { recs.forEach(function (r, i) { r.sc = after[i]; applyRec(r); }); remark(); } });
    remark(); refreshPanel();
  }
  function duplicate() {
    if (!SEL.length) return;
    if (SEL.length === 1) {
      /* the copy rides the cursor; click puts it down and selects it */
      var r0 = SEL[0];
      armed = r0.key;
      placeRot = r0.rot;
      placeScale = r0.sc;
      runPrev = runMode ? r0 : null; runSlot = null;
      setMode('place');
      makeGhost(r0.key);
      toast('copy on the cursor · click to place');
      return;
    }
    var made = SEL.map(function (r) {
      return addObject(r.key, r.x + 3, r.y, r.z + 3, r.rot, r.sc, true);
    });
    push({ undo: function () { made.forEach(removeRecord); refreshList(); },
           redo: function () { made.forEach(reAdd); refreshList(); } });
    SEL.forEach(unmark); SEL.length = 0;
    made.forEach(function (r) { SEL.push(r); mark(r); });
    refreshPanel(); refreshList(); updateGizmo();
    toast('duplicated ' + made.length + ' · the copies are selected');
  }
  function del() {
    if (!SEL.length) return;
    var gone = SEL.slice();
    gone.forEach(unmark);
    gone.forEach(removeRecord);
    SEL.length = 0;
    push({ undo: function () { gone.forEach(reAdd); refreshList(); },
           redo: function () { gone.forEach(removeRecord); refreshList(); } });
    refreshPanel(); refreshList(); toast('deleted ' + gone.length);
  }

  function refreshSnap() {
    $('snapGrid').textContent = snapGrid ? 'Grid 1m' : 'Grid off';
    $('snapGrid').classList.toggle('on', snapGrid);
    $('snapGround').textContent = snapGround ? 'Sit on ground' : 'Free height';
    $('snapGround').classList.toggle('on', snapGround);
  }

  /* --------------------------------------------------------------- wire */
  function wireUI() {
    $('mSelect').onclick = function () { armed = null; setMode('select'); };
    $('mLand').onclick = function () { landInit(); setMode('land'); };
    ['Raise', 'Lower', 'Smooth', 'Flat', 'Water', 'Dry'].forEach(function (nm) {
      $('lb' + nm).onclick = function () {
        landBrush = nm.toLowerCase();
        document.querySelectorAll('.lb').forEach(function (q) { q.classList.remove('on'); });
        $('lb' + nm).classList.add('on');
      };
    });
    $('lbRad').oninput = function () { landRad = +this.value; $('lbRadV').textContent = this.value; };
    $('lbStr').oninput = function () { landStr = +this.value; $('lbStrV').textContent = this.value; };
    $('lbReset').onclick = function () {
      if (!LAND) landInit();
      LAND.elev.fill(0); LAND.water.fill(0);
      landDirty = true; landSave();
      W.touchTerrain(0, 0, LAND.size);
      toast('the land is flat again');
    };
    $('grp').onclick = groupSel;
    $('ungrp').onclick = ungroupSel;
    $('mPlace').onclick = function () { setMode('place'); if (!armed) toast('pick an asset on the left'); };
    if ($('mScatter')) {
      $('mScatter').onclick = function () {
        setMode('scatter');
        if (!armed && !MIX.length) toast('pick an asset on the left, or build a mix');
      };
      $('bAdd').onclick = function () {
        var added = 0;
        if (armed && MIX.indexOf(armed) < 0) { MIX.push(armed); added++; }
        SEL.forEach(function (r) { if (r.key && MIX.indexOf(r.key) < 0) { MIX.push(r.key); added++; } });
        mixLabel();
        toast(added ? ('mix has ' + MIX.length) : 'nothing new to add');
      };
      $('bClr').onclick = function () { MIX.length = 0; mixLabel(); };
      mixLabel();
    }
    $('snapGrid').onclick = function () { snapGrid = !snapGrid; refreshSnap(); };
    $('snapGround').onclick = function () { snapGround = !snapGround; refreshSnap(); };
    $('undo').onclick = undo;
    $('redo').onclick = redo;
    $('save').onclick = save;
    $('load2').onclick = function () { loadSaved(); };
    $('del').onclick = del;
    $('dup').onclick = duplicate;
    $('row').onclick = function () {
      if (SEL.length !== 1) { toast('select one thing to grow a row from'); return; }
      var r0 = SEL[0];
      armed = r0.key;
      placeRot = r0.rot;
      placeScale = r0.sc;
      runMode = true;
      runPrev = r0; runSlot = null;
      setMode('place');
      makeGhost(r0.key);
      toast('row: click to add one beside it · [ ] to turn a corner · T to stop');
    };
    $('clear').onclick = function () {
      if (!PLACED.length) return;
      var all = PLACED.slice();
      all.forEach(removeRecord);
      SEL.length = 0;
      push({ undo: function () { all.forEach(reAdd); refreshList(); },
             redo: function () { all.forEach(removeRecord); refreshList(); } });
      refreshList(); refreshPanel(); toast('cleared');
    };
    $('exp').onclick = function () {
      var blob = new Blob([JSON.stringify({ layout: serialise() }, null, 1)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'town.json';
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
    };
    $('imp').onclick = function () { $('file').click(); };
    $('file').onchange = function (e) {
      var f = e.target.files[0];
      if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        try {
          var j = JSON.parse(r.result);
          loadLayout(j.layout || j);
        } catch (err) { toast('bad file: ' + err.message); }
      };
      r.readAsText(f);
      e.target.value = '';
    };
    $('day').onclick = function () {
      W.setDaylight(!W.DAYLIGHT);
      $('day').textContent = W.DAYLIGHT ? 'Daylight' : 'Night';
      $('day').classList.toggle('on', W.DAYLIGHT);
      W.wake();
    };
    $('play').onclick = function () {
      try { localStorage.setItem(STORE, JSON.stringify(serialise())); } catch (e) {}
      location.href = 'index.html?layout=1&t=' + Date.now();
    };
    $('town').onclick = function () {
      toast('building the town…');
      setTimeout(seedTown, 30);
    };

    ['px', 'py', 'pz', 'ry', 'sc'].forEach(function (id) {
      $(id).onchange = function () {
        if (SEL.length !== 1) return;
        var r = SEL[0], v = parseFloat(this.value);
        if (isNaN(v)) return;
        if (id === 'px') r.x = v; else if (id === 'py') r.y = v; else if (id === 'pz') r.z = v;
        else if (id === 'ry') r.rot = v * Math.PI / 180; else r.sc = Math.max(0.05, v);
        applyRec(r); remark();
      };
    });

    $('search').oninput = function () {
      var q = this.value.trim().toLowerCase();
      document.querySelectorAll('.grp').forEach(function (g) {
        var any = false;
        g.querySelectorAll('.item').forEach(function (it) {
          var hit = !q || it.dataset.search.indexOf(q) >= 0;
          it.style.display = hit ? '' : 'none';
          if (hit) any = true;
        });
        g.style.display = any ? '' : 'none';
        if (q) g.classList.add('open');
      });
    };

    $('hint').innerHTML =
      'WASD fly · Q/E down/up · Shift fast · right-drag look · wheel zoom<br>' +
      'click an asset then click the ground to place · click a building for its handles:<br>' +
      'red/blue arrows slide it, green arrow lifts it, yellow square slides it freely, gold ring turns it<br>' +
      '[ ] turn · + − size · Ctrl+D copy · T row · Del remove · Ctrl+Z undo · G grid';
  }

  /* A starting town, so the page is not an empty desert. It is only a seed:
     everything it puts down is an ordinary object you can move or delete. */
  function seedTown() {
    var made = [];
    function put(k, x, z, rot, sc) {
      made.push(addObject(k, x, W.heightAt(x, z), z, rot || 0, sc || 1, true));
    }
    var fams = ['kit/house_1', 'kit/house_5', 'kit/house_9', 'kit/tower_2', 'kit/tower_7',
                'kit/court_3', 'kit/court_8', 'kit/shops_4', 'kit/shops_11',
                'kit/riad_6', 'kit/block_10', 'kit/block_13'];
    var avail = fams.filter(function (f) { return true; });
    var n = 0;
    for (var ring = 0; ring < 4; ring++) {
      var count = 6 + ring * 4;
      var rad = 26 + ring * 26;
      for (var i = 0; i < count; i++) {
        var a = (i / count) * Math.PI * 2 + ring * 0.4;
        var x = Math.cos(a) * rad + (Math.random() - 0.5) * 9;
        var z = Math.sin(a) * rad + (Math.random() - 0.5) * 9;
        put(avail[(n++) % avail.length], x, z, -a + Math.PI / 2 + (Math.random() - 0.5) * 0.4);
      }
    }
    made.forEach(function () {});
    refreshList();
    push({ undo: function () { made.forEach(removeRecord); refreshList(); },
           redo: function () { made.forEach(reAdd); refreshList(); } });
    toast('placed ' + made.length + ' buildings · move or delete any of them');
  }

  /* -------------------------------------------------------------- start */
  W.startEditor = function () {
    W.EDITOR = true;
    /* A level plain to build on, above the water table. Without it the middle
       of the map is whatever the noise happened to make there, which the first
       time was the bottom of a lake -- the town went in underwater. The rest
       of the world is untouched; this is only somewhere sensible to start. */
    var natural = W.heightAt(0, 0);
    var padY = Math.max(natural, W.WATER_Y + 9);
    W.addFlat(0, 0, 420, padY, 150);
    W.PAD_Y = padY;
    W.start();
    T = THREE;
    scene = W.scene; cam = W.cam; renderer = W.renderer;
    rc = new T.Raycaster();
    loader = new T.GLTFLoader();
    GIZ = buildGizmo();

    var l = $('load'); if (l) l.style.display = 'none';
    W.setDaylight(true);
    W.camState({ x: 0, y: W.PAD_Y + 42, z: 150, yaw: 0, pitch: -0.42 });
    wireUI();
    refreshSnap();
    refreshBar();
    bindInput();
    setMode('select');

    fetch('assets/manifest.json?t=' + Date.now())
      .then(function (r) { return r.json(); })
      .then(function (m) {
        buildTree(m);
        var n = 0; m.groups.forEach(function (g) { n += g.items.length; });
        toast(n + ' assets ready');
      })
      .catch(function (e) { W.diag('no asset manifest: ' + e.message); });

    if (!loadSaved(true)) {
      /* nothing saved · leave the world empty and tell them how to fill it */
      setTimeout(function () { toast('pick an asset on the left, or press "Add the town"'); }, 900);
    }
    setInterval(function () {
      var hb = $('hb');
      if (hb && W.renderer) hb.textContent = PLACED.length + ' obj · ' +
        Math.round(W.renderer.info.render.triangles / 1000) + 'k tris';
    }, 1000);
  };
})();
