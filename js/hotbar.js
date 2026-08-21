/* THE HOTBAR, AND WHAT EACH RELIC DOES WHEN IT IS IN HER HAND.
   =================================================================
   Seven slots along the bottom. Five carry the relics; two are left empty on
   purpose, because a bar with exactly as many slots as there are things in it
   says the collection is finished.

   ONE RULE HOLDS THIS TOGETHER: a relic is a MODEL plus a BEHAVIOUR, and the
   two are declared in the same place. Everything a relic does when equipped -
   where it sits, whether it can be swung, what it leaves in the air - is in
   its entry in RELICS below, so adding the sixth is adding one object and
   nothing else.

   The trails are all one mechanism, from relicfx.js: something released at a
   point, with a little sideways drift, that sinks slowly, turns, and fades
   out over its life. A swung sword leaves motes along the arc; a flying
   carpet leaves them behind it; a beating wing sheds stones; a swung staff
   drops petals and leaves. They differ in what falls and how long for, and in
   nothing else. */
(function () {
  'use strict';
  var W = window.W = window.W || {};
  var T = window.THREE;

  var SAVE = 'amirat.hotbar.v1';

  /* ------------------------------------------------------------ the relics
     `hold` is where the thing sits relative to the camera, in the camera's
     own frame: x right, y up, z back. A held object is placed there every
     frame rather than parented, so it can lag behind the look and swing
     without fighting the camera's own rotation. */
  var RELICS = [
    { k: 'sabre', ar: 'السَّيْف', en: 'Sabre', scale: 1.0,
      hold: [0.34, -0.30, -0.62], rot: [-0.30, 0.42, 0.18],
      act: 'swing', swing: 0.42,
      trail: { kind: 'mote', n: 3, life: 6.0, size: 0.030, col: 0xff5fb4 } },

    { k: 'carpet', ar: 'البِسَاط', en: 'Carpet', scale: 1.0,
      hold: [0.0, -1.15, 0.10], rot: [0, 0, 0], carry: 'under',
      act: 'fly',
      trail: { kind: 'mote', n: 2, life: 6.5, size: 0.045, multi: 1 } },

    { k: 'wings', ar: 'الأَجْنِحَة', en: 'Wings', scale: 1.0,
      hold: [0.0, -0.10, 0.42], rot: [0, 0, 0], carry: 'back',
      act: 'flap' },

    { k: 'wand', ar: 'العَصَا', en: 'Staff', scale: 1.0,
      hold: [0.30, -0.85, -0.50], rot: [-0.16, 0.30, 0.10],
      act: 'swing', swing: 0.52,
      trail: { kind: 'petal', n: 4, life: 6.0, size: 0.030 } },

    { k: 'astrolabe', ar: 'الأَسْطُرْلَاب', en: 'Astrolabe', scale: 0.62,
      hold: [0.26, -0.24, -0.48], rot: [0.10, 0.30, 0],
      act: 'read' }
  ];

  var SLOTS = 7;
  var loaded = {};          /* k -> { root, fx, dressed } */
  var held = null;          /* the one in her hand */
  var cur = -1;
  var bar = null, chips = [];
  var trails = null;        /* the falling things, one pool per kind */

  /* -------------------------------------------------------------- the save */
  function remember() {
    try { localStorage.setItem(SAVE, String(cur)); } catch (e) {}
  }
  function recall() {
    try {
      var v = parseInt(localStorage.getItem(SAVE), 10);
      return isNaN(v) ? -1 : v;
    } catch (e) { return -1; }
  }

  /* -------------------------------------------------------------- the bar */
  function build() {
    bar = document.createElement('div');
    bar.id = 'hotbar';
    for (var i = 0; i < SLOTS; i++) {
      var c = document.createElement('button');
      c.type = 'button';
      c.className = 'slot';
      c.setAttribute('data-i', String(i));
      var r = RELICS[i];
      c.innerHTML = '<span class="num">' + (i + 1) + '</span>' +
        (r ? '<span class="ar"></span><span class="en"></span>'
           : '<span class="empty"></span>');
      if (r) {
        c.querySelector('.ar').textContent = r.ar;
        c.querySelector('.en').textContent = r.en;
      }
      (function (n) {
        c.addEventListener('click', function () { equip(n === cur ? -1 : n); });
      })(i);
      bar.appendChild(c);
      chips.push(c);
    }
    document.body.appendChild(bar);

    /* 1..7 pick a slot; 0 or Escape puts it away. Captured before the engine
       sees it, because the engine treats keys as movement. */
    window.addEventListener('keydown', function (e) {
      if (W.UI_OPEN) return;
      if (e.key >= '1' && e.key <= '7') {
        var n = parseInt(e.key, 10) - 1;
        equip(n === cur ? -1 : n);
        e.preventDefault();
      } else if (e.key === '0') {
        equip(-1);
      } else if (e.code === 'KeyQ') {
        use();
      }
    }, true);

    /* and the mouse, once she is in the world */
    addEventListener('pointerdown', function (e) {
      if (W.UI_OPEN) return;
      if (e.button === 0 && cur >= 0) use();
    });
  }

  var hintEl = null, hintT = 0;
  var HINT = {
    swing: 'Click to swing',
    fly: 'She is flying · put it away to come down',
    flap: 'They beat on their own',
    read: 'Click to open the readings'
  };

  function paint() {
    for (var i = 0; i < chips.length; i++) {
      chips[i].setAttribute('aria-selected', i === cur ? 'true' : 'false');
    }
    if (!hintEl) {
      hintEl = document.createElement('div');
      hintEl.id = 'relichint';
      document.body.appendChild(hintEl);
    }
    if (cur < 0) { hintEl.classList.remove('on'); return; }
    var R = RELICS[cur];
    hintEl.textContent = R.en + ' · ' + (HINT[R.act] || '');
    hintEl.classList.add('on');
    clearTimeout(hintT);
    hintT = setTimeout(function () { hintEl.classList.remove('on'); }, 4200);
  }

  /* --------------------------------------------------------- fetching them
     A relic is loaded the first time it is chosen and kept, because the
     wings alone are two hundred thousand triangles and nobody wants to wait
     for that twice. */
  function fetchRelic(k) {
    if (loaded[k]) return Promise.resolve(loaded[k]);
    if (!W.GLTF) W.GLTF = new T.GLTFLoader();
    var v = window.__BUILD || '';
    return Promise.all([
      fetch('assets/models/relic/' + k + '.fx.json?v=' + v)
        .then(function (r) { return r.json(); }).catch(function () { return {}; }),
      new Promise(function (res, rej) {
        W.GLTF.load('assets/models/relic/' + k + '.glb?v=' + v,
          function (g) { res(g.scene); }, undefined, rej);
      })
    ]).then(function (a) {
      var fx = a[0], root = a[1];
      /* centre it on its own middle so it can be held without guessing */
      var bb = new T.Box3().setFromObject(root);
      var c = new T.Vector3(); bb.getCenter(c);
      root.position.set(-c.x, -c.y, -c.z);
      var pivot = new T.Group();
      pivot.add(root);
      var dressed = W.dressRelic(pivot, fx, k, W.scene);
      dressed.group.visible = false;
      loaded[k] = { root: root, pivot: pivot, fx: fx, dressed: dressed,
                    size: bb.getSize(new T.Vector3()) };
      return loaded[k];
    }).catch(function (e) {
      if (W.diag) W.diag('relic ' + k + ' did not load: ' + e.message);
      return null;
    });
  }

  /* --------------------------------------------------------------- equip */
  function equip(n) {
    if (held) { held.dressed.group.visible = false; held = null; }
    if (n === cur) n = -1;
    cur = (n >= 0 && n < RELICS.length) ? n : -1;
    paint();
    remember();
    /* THE CARPET IS THE ONLY THING THAT FLIES. Taking it out is what lifts
       her; putting it away is what sets her down. */
    if (W.setFly) W.setFly(cur >= 0 && RELICS[cur].act === 'fly');
    if (cur < 0) return;
    var R = RELICS[cur];
    fetchRelic(R.k).then(function (L) {
      if (!L || cur < 0 || RELICS[cur].k !== R.k) return;
      held = L;
      L.dressed.group.visible = true;
      L.spec = R;
      L.swing = 0;
      L.swingT = 0;
    });
  }
  W.equip = equip;
  W.equipped = function () { return cur >= 0 ? RELICS[cur] : null; };

  /* ----------------------------------------------------------------- use */
  function use() {
    if (!held) return;
    var R = held.spec;
    if (R.act === 'swing') {
      if (held.swing > 0) return;            /* already mid-stroke */
      held.swing = 1;
      held.swingT = 0;
    } else if (R.act === 'read') {
      if (W.uiOpen) W.uiOpen('shelf');
    }
  }
  W.useHeld = use;

  /* ------------------------------------------------------- what falls off */
  function makeTrails() {
    if (trails) return trails;
    trails = {};
    /* a mote: a soft round grain of light */
    var moteGeo = new T.PlaneGeometry(1, 1);
    trails.mote = W.makeFall(moteGeo, new T.MeshBasicMaterial({
      map: W.moteTexture ? W.moteTexture() : null,
      transparent: true, depthWrite: false, blending: T.AdditiveBlending,
      toneMapped: false, vertexColors: true
    }), 140);
    /* a petal: a small curved sliver, and a leaf beside it */
    var petGeo = new T.CircleGeometry(1, 6);
    petGeo.scale(1, 1.7, 1);
    var ones = new Float32Array(petGeo.attributes.position.count * 3);
    for (var i = 0; i < ones.length; i++) ones[i] = 1;
    petGeo.setAttribute('color', new T.BufferAttribute(ones, 3));
    trails.petal = W.makeFall(petGeo, new T.MeshStandardMaterial({
      color: 0xffffff, roughness: 0.85, metalness: 0, side: T.DoubleSide,
      transparent: true, depthWrite: false, vertexColors: true
    }), 120);
    W.scene.add(trails.mote.mesh);
    W.scene.add(trails.petal.mesh);
    return trails;
  }

  var PETAL_COL = new T.Color(0xf07ab0);
  var LEAF_COL = new T.Color(0x7ab86a);
  var TMP = new T.Color();

  function drop(kind, x, y, z, opt) {
    var Tr = makeTrails();
    var F = Tr[kind === 'petal' ? 'petal' : 'mote'];
    if (!F) return;
    W.fallEmit(F, x, y, z, opt);
  }

  /* ---------------------------------------------------------------- drive */
  var camDir = new T.Vector3(), camRight = new T.Vector3(), camUp = new T.Vector3();
  var tmp = new T.Vector3(), lastTip = new T.Vector3(), tipNow = new T.Vector3();

  W.tickHotbar = function (dt, t) {
    if (trails) {
      W.fallDrive(trails.mote, dt, t);
      W.fallDrive(trails.petal, dt, t);
    }
    if (!held) return;
    var R = held.spec, g = held.dressed.group, cam = W.cam;
    cam.updateMatrixWorld();
    camDir.set(0, 0, -1).applyQuaternion(cam.quaternion);
    camRight.set(1, 0, 0).applyQuaternion(cam.quaternion);
    camUp.set(0, 1, 0).applyQuaternion(cam.quaternion);

    /* A THING SHE IS CARRYING DOES NOT TILT WHEN SHE LOOKS DOWN.
       A held sword lives in the camera's own frame, which is right: it is in
       her hand and her hand goes where she looks. A carpet under her feet and
       a pair of wings on her back do NOT - they belong to her body, not to
       her head, so they use a frame built from the YAW alone. Given the full
       camera frame, looking down at the ground swung the carpet out behind
       her and off the screen entirely, which is exactly what happened. */
    var body = !!R.carry;
    var yaw = W.getYaw ? W.getYaw() : 0;
    var fx = -Math.sin(yaw), fz = -Math.cos(yaw);      /* forward, flat */
    var rx = Math.cos(yaw), rz = -Math.sin(yaw);       /* right, flat */

    var h = R.hold;
    if (body) {
      tmp.set(cam.position.x + rx * h[0] - fx * h[2],
              cam.position.y + h[1],
              cam.position.z + rz * h[0] - fz * h[2]);
    } else {
      tmp.copy(cam.position)
        .addScaledVector(camRight, h[0])
        .addScaledVector(camUp, h[1])
        .addScaledVector(camDir, -h[2]);
    }

    var sw = 0;
    if (held.swing > 0) {
      held.swingT += dt;
      var d = R.swing || 0.42;
      var u = held.swingT / d;
      if (u >= 1) { held.swing = 0; held.swingT = 0; u = 1; }
      /* THE STROKE. It winds up slowly, comes through fast, and recovers -
         which is what makes it read as weight being moved rather than as a
         thing being rotated. */
      sw = u < 0.22 ? -(u / 0.22) * 0.45
                    : Math.sin((u - 0.22) / 0.78 * Math.PI) * 2.5 - 0.45 * (1 - (u - 0.22) / 0.78);
    }

    g.position.copy(tmp);
    if (body) {
      /* level, and turned to face the way she is going */
      g.rotation.set(R.rot[0], yaw + R.rot[1], R.rot[2]);
    } else {
      g.quaternion.copy(cam.quaternion);
      g.rotateX(R.rot[0]);
      g.rotateY(R.rot[1]);
      g.rotateZ(R.rot[2] + sw);
    }
    g.scale.setScalar(R.scale || 1);

    /* WHAT IT LEAVES BEHIND.
       A swing lays its trail along the ARC the tip actually travelled, not at
       one point - the tip is sampled this frame and last, and the grains are
       strung between them, or a fast stroke leaves a dotted line with holes
       in it. */
    if (R.trail) {
      var wantTrail = false, spread = 0.10, rise = 0.02;
      if (R.act === 'swing' && held.swing > 0) wantTrail = true;
      if (R.act === 'fly' && W.isFlying && W.isFlying()) {
        wantTrail = true; spread = 0.22; rise = 0.05;
      }
      if (wantTrail) {
        /* THE TIP IS THE MODEL'S OWN TIP, not a guess made from the camera.
           Every relic here is built standing along its local +Y, so the point
           that actually travels is the group's own up-axis times half its
           height - which means the trail is laid along the arc the BLADE
           swept, and it stays right when the stroke turns the thing over. A
           point derived from the camera instead sits wherever the camera is
           looking and has nothing to do with where the sword went. */
        var reach = held.size ? held.size.y * 0.5 : 0.5;
        tipNow.set(0, 1, 0).applyQuaternion(g.quaternion)
          .multiplyScalar(reach).add(g.position);
        if (!held.hadTip) { lastTip.copy(tipNow); held.hadTip = 1; }
        var n = R.trail.n || 3;
        for (var i = 0; i < n; i++) {
          var f = (i + 0.5) / n;
          var px = lastTip.x + (tipNow.x - lastTip.x) * f;
          var py = lastTip.y + (tipNow.y - lastTip.y) * f;
          var pz = lastTip.z + (tipNow.z - lastTip.z) * f;
          if (R.trail.kind === 'petal') {
            /* petals AND leaves, because a tree in flower drops both */
            var leaf = Math.random() < 0.34;
            TMP.copy(leaf ? LEAF_COL : PETAL_COL);
            drop('petal', px, py, pz,
                 { life: R.trail.life, size: R.trail.size * (leaf ? 0.8 : 1),
                   spread: spread, rise: rise, col: TMP });
          } else {
            if (R.trail.multi) {
              /* the carpet's five colours, not one */
              TMP.setHex([0xff77c8, 0xc98bff, 0x8ab6ff, 0xffffff,
                          0xffd98a][(Math.random() * 5) | 0]);
            } else {
              TMP.setHex(R.trail.col || 0xff5fb4);
            }
            drop('mote', px, py, pz,
                 { life: R.trail.life, size: R.trail.size,
                   spread: spread, rise: rise, col: TMP });
          }
        }
        lastTip.copy(tipNow);
      } else {
        held.hadTip = 0;
      }
    }

    /* a swing brightens what is swung */
    if (held.dressed.lit && R.act === 'swing') {
      var boost = held.swing > 0 ? 1.35 : 1.0;
      for (var m = 0; m < held.dressed.lit.length; m++) {
        var mm = held.dressed.lit[m];
        if (mm.__base === undefined) mm.__base = mm.__b || mm.emissiveIntensity;
        mm.__b = mm.__base * boost;
      }
    }

    held.dressed.tick(t, cam.position, dt);
  };

  /* a probe hook: what is actually in her hand right now */
  W.trailsNow = function () {
    if (!trails) return null;
    function live(F) { return F.pool.filter(function (p) { return p.live; }).length; }
    return { mote: live(trails.mote), petal: live(trails.petal) };
  };
  W.heldNow = function () {
    return held ? { k: held.spec.k, vis: held.dressed.group.visible,
                    at: held.dressed.group.position.toArray().map(function (v) {
                      return +v.toFixed(2); }),
                    swing: held.swing } : null;
  };
  W.hotbarBuild = build;
  W.hotbarRestore = function () {
    var v = recall();
    if (v >= 0 && v < RELICS.length) equip(v);
    else paint();
  };
  W.RELICS = RELICS;
})();
