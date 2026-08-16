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
  var mode = 'select';       /* 'select' | 'place' */
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
      if (!src) return;
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
    var i = PLACED.indexOf(rec);
    if (i >= 0) PLACED.splice(i, 1);
    if (rec.obj) scene.remove(rec.obj);
    var s = SEL.indexOf(rec);
    if (s >= 0) SEL.splice(s, 1);
  }
  function reAdd(rec) {
    PLACED.push(rec);
    if (rec.obj) scene.add(rec.obj);
    else getModel(rec.key, function (src) {
      if (!src) return;
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

  function placeAt(key, p) {
    var y = snapGround ? W.heightAt(p.x, p.z) : p.y;
    var x = p.x, z = p.z;
    if (snapGrid) { x = Math.round(x / GRID) * GRID; z = Math.round(z / GRID) * GRID; }
    var rec = addObject(key, x, y, z, Math.random() * Math.PI * 2, 1);
    push({ undo: function () { removeRecord(rec); }, redo: function () { reAdd(rec); } });
    return rec;
  }

  /* ---------------------------------------------------------- selection */
  function clearSel() { SEL.forEach(unmark); SEL.length = 0; refreshPanel(); refreshList(); }
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
    refreshPanel(); refreshList();
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
      while (o && !o.userData.rec) o = o.parent;
      if (o) return { rec: o.userData.rec, point: hits[i].point };
    }
    return null;
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
          setMode('place');
          makeGhost(it.k);
          toast('placing ' + it.n);
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
    if (m === 'select' && ghost) { ghost.visible = false; }
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

  function refreshList() {
    var box = $('objs');
    box.innerHTML = '';
    var n = Math.min(PLACED.length, 400);
    for (var i = PLACED.length - 1; i >= PLACED.length - n; i--) {
      (function (rec) {
        var e = document.createElement('div');
        e.className = 'o' + (SEL.indexOf(rec) >= 0 ? ' sel' : '');
        e.textContent = rec.key;
        e.onclick = function (ev) { select(rec, ev.ctrlKey || ev.shiftKey); focusOn(rec); };
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
      return { k: p.key, p: [fmt(p.x), fmt(p.y), fmt(p.z)], r: fmt(p.rot), s: fmt(p.sc) };
    });
  }
  function loadLayout(list, quiet) {
    PLACED.slice().forEach(removeRecord);
    SEL.length = 0;
    list.forEach(function (o) {
      addObject(o.k, o.p[0], o.p[1], o.p[2], o.r || 0, o.s === undefined ? 1 : o.s, true);
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

    addEventListener('keydown', function (e) {
      if (/^(INPUT|TEXTAREA)$/.test((e.target.tagName || ''))) return;
      keys[e.code] = true;
      var ctrl = e.ctrlKey || e.metaKey;
      if (ctrl && e.code === 'KeyZ') { e.preventDefault(); undo(); }
      else if (ctrl && (e.code === 'KeyY' || (e.shiftKey && e.code === 'KeyZ'))) { e.preventDefault(); redo(); }
      else if (ctrl && e.code === 'KeyD') { e.preventDefault(); duplicate(); }
      else if (ctrl && e.code === 'KeyS') { e.preventDefault(); save(); }
      else if (e.code === 'Delete' || e.code === 'Backspace') { e.preventDefault(); del(); }
      else if (e.code === 'Escape') { armed = null; setMode('select'); clearSel(); }
      else if (e.code === 'KeyG') { snapGrid = !snapGrid; refreshSnap(); }
      else if (e.code === 'KeyR') { dragRot = true; }
      else if (e.code === 'BracketLeft') { nudgeRot(-Math.PI / 12); }
      else if (e.code === 'BracketRight') { nudgeRot(Math.PI / 12); }
      else if (e.code === 'Equal' || e.code === 'NumpadAdd') { nudgeScale(1.08); }
      else if (e.code === 'Minus' || e.code === 'NumpadSubtract') { nudgeScale(1 / 1.08); }
      W.wake();
    });
    addEventListener('keyup', function (e) {
      keys[e.code] = false;
      if (e.code === 'KeyR') dragRot = false;
    });
    addEventListener('blur', function () { keys = {}; });

    cv.addEventListener('contextmenu', function (e) { e.preventDefault(); });

    cv.addEventListener('pointerdown', function (e) {
      cv.setPointerCapture(e.pointerId);
      mouse.down = true; mouse.btn = e.button;
      mouse.sx = e.clientX; mouse.sy = e.clientY; mouse.moved = 0;
      mouse.look = (e.button === 2);
      dragVert = keys['KeyZ'];
      if (e.button === 0 && mode === 'select') {
        var hit = pickObject(e);
        if (hit) {
          if (SEL.indexOf(hit.rec) < 0) select(hit.rec, e.ctrlKey || e.shiftKey);
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
      if (mode === 'place' && ghost) {
        var g = groundPoint(e);
        if (g) {
          if (snapGrid) { g.x = Math.round(g.x / GRID) * GRID; g.z = Math.round(g.z / GRID) * GRID; }
          ghost.position.set(g.x, g.y, g.z);
          ghost.visible = true;
        } else ghost.visible = false;
        W.wake();
      }
      if (mouse.down && mouse.btn === 0 && dragStart && SEL.length) {
        dragSelection(e);
        W.wake();
      }
    });

    cv.addEventListener('pointerup', function (e) {
      cv.releasePointerCapture(e.pointerId);
      var wasDrag = mouse.moved > 6;
      mouse.down = false; mouse.look = false;
      if (e.button === 0 && mode === 'place' && armed && !wasDrag) {
        var g = groundPoint(e);
        if (g) placeAt(armed, g);
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

  function nudgeRot(d) {
    if (!SEL.length) return;
    var recs = SEL.slice(), before = recs.map(function (r) { return r.rot; });
    recs.forEach(function (r) { r.rot += d; applyRec(r); });
    var after = recs.map(function (r) { return r.rot; });
    push({ undo: function () { recs.forEach(function (r, i) { r.rot = before[i]; applyRec(r); }); },
           redo: function () { recs.forEach(function (r, i) { r.rot = after[i]; applyRec(r); }); } });
    refreshPanel();
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
    var made = SEL.map(function (r) {
      return addObject(r.key, r.x + 3, r.y, r.z + 3, r.rot, r.sc, true);
    });
    push({ undo: function () { made.forEach(removeRecord); refreshList(); },
           redo: function () { made.forEach(reAdd); refreshList(); } });
    refreshList(); toast('duplicated ' + made.length);
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
    $('mPlace').onclick = function () { setMode('place'); if (!armed) toast('pick an asset on the left'); };
    $('snapGrid').onclick = function () { snapGrid = !snapGrid; refreshSnap(); };
    $('snapGround').onclick = function () { snapGround = !snapGround; refreshSnap(); };
    $('undo').onclick = undo;
    $('redo').onclick = redo;
    $('save').onclick = save;
    $('load2').onclick = function () { loadSaved(); };
    $('del').onclick = del;
    $('dup').onclick = duplicate;
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
      'click an asset then click the ground to place · drag to move · Z-drag for height · R-drag to turn<br>' +
      '[ ] turn · + − size · Ctrl+D copy · Del remove · Ctrl+Z undo · G grid';
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
