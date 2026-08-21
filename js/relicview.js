/* THE ROOM THE RELICS ARE SHOWN IN.
   =================================================================
   A turntable in a dark room. There is almost nothing here on purpose: the
   point is to judge whether a thing makes its own light, and you cannot judge
   that against a lit background or a busy one. So: a black floor that catches
   a little of the relic's own colour, two very low fills so the unlit side of
   an object is not pure void, and bloom.

   It shares js/relicfx.js with the world, so what is judged here is exactly
   what will be standing in the town - not a prettier version of it. */
(function () {
  'use strict';
  var T = window.THREE;
  var W = window.W = window.W || {};

  var RELICS = [
    { k: 'sabre', ar: 'السَّيْف', en: 'The Sabre',
      note: 'A curved saif, its fuller lit from within, on a bound grip and a round pommel.',
      dist: 1.9, at: 0.02, spin: 0.20 },
    { k: 'carpet', ar: 'البِسَاط', en: 'The Carpet',
      note: 'A field of raised bosses and a knotted border, with the light coming up out of the weave.',
      dist: 2.9, at: 0.14, spin: 0.13 },
    { k: 'wings', ar: 'الأَجْنِحَة', en: 'The Wings',
      note: 'Every feather has a lit quill down its shaft and a stone set in its vane.',
      dist: 2.5, at: 0.05, spin: 0.16 },
    { k: 'wand', ar: 'العَصَا', en: 'The Staff',
      note: 'Dark wood that kept the shape it grew in, with blossom breaking out of the old scars.',
      dist: 3.0, at: 0.05, spin: 0.18 },
    { k: 'astrolabe', ar: 'الأَسْطُرْلَاب', en: 'The Astrolabe',
      note: 'A pierced sky turning over an engraved plate, with a star at the point of every one of its fourteen pointers.',
      dist: 1.30, at: 0.05, spin: 0.14 }
  ];

  var scene, cam, renderer, composer, clock;
  var cur = null, dressed = null, loader;
  var yaw = 0.6, pitch = 0.10, dist = 2.2, want = 2.2;
  var spin = 0.2, target = new T.Vector3(0, 0.5, 0);

  /* A WINDOW CAN HAVE NO SIZE. A tab that is loaded while it is not being
     displayed reports innerWidth 0, and a composer built at 0 by 0 makes its
     render targets that size - after which every frame it produces is a flat
     smear, whatever you resize it to afterwards. Nothing warns you. Every
     size this page uses goes through here. */
  function vw() { return Math.max(window.innerWidth || 0, 640); }
  function vh() { return Math.max(window.innerHeight || 0, 480); }

  function boot() {
    renderer = new T.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.setSize(vw(), vh());
    renderer.outputEncoding = T.sRGBEncoding;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    document.body.appendChild(renderer.domElement);

    scene = new T.Scene();
    scene.background = new T.Color(0x0b0907);
    scene.fog = new T.FogExp2(0x0b0907, 0.10);

    cam = new T.PerspectiveCamera(38, vw() / vh(), 0.05, 60);

    /* THE ROOM. Two fills only, and both are nearly nothing: enough that the
       far side of a blade is not a black hole, not enough to light the object
       for it. Everything you actually see is coming out of the relic. */
    scene.add(new T.HemisphereLight(0x50506a, 0x140f0a, 0.42));
    var key = new T.DirectionalLight(0xbfc6e0, 0.80);
    key.position.set(2.4, 4.0, 2.0);
    scene.add(key);

    /* the floor: dark, and just glossy enough to take a smear of the relic's
       own colour, which is what tells you the light is real */
    /* something for the metal to reflect, or gold reads as coal */
    scene.environment = W.relicEnv(renderer);

    var fl = new T.Mesh(
      new T.CircleGeometry(9, 48),
      new T.MeshStandardMaterial({ color: 0x14100c, roughness: 0.46, metalness: 0.10 })
    );
    fl.rotation.x = -Math.PI / 2;
    scene.add(fl);

    var rp = new T.RenderPass(scene, cam);
    composer = new T.EffectComposer(renderer);
    composer.addPass(rp);
    /* THE HALO WAS EATING THE THING IT CAME OFF.
       Proved by turning it off: with strength at zero the carpet's flowers
       are visibly pink and in relief, and with it at 1.05 every one of them
       was a white blob. A wide bloom does not make a small bright thing look
       brighter - it replaces it. Tight radius, higher threshold: only what is
       genuinely burning gets a halo, and the halo stays near it. */
    var bloom = new T.UnrealBloomPass(new T.Vector2(vw(), vh()), 0.72, 0.42, 0.55);
    composer.addPass(bloom);

    clock = new T.Clock();
    loader = new T.GLTFLoader();

    buildPicker();
    controls();
    addEventListener('resize', onResize);
    show(0);
    requestAnimationFrame(frame);
    /* and if animation frames are starved, a plain timer keeps it alive */
    setInterval(function () {
      if (performance.now() - lastRaf > 400) {
        try { step(0.033); } catch (e) {}
      }
    }, 250);
  }

  function onResize() {
    cam.aspect = vw() / vh();
    cam.updateProjectionMatrix();
    renderer.setSize(vw(), vh());
    composer.setSize(vw(), vh());
  }

  function buildPicker() {
    var nav = document.getElementById('pick');
    RELICS.forEach(function (r, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = r.en;
      b.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      b.addEventListener('click', function () { show(i); });
      nav.appendChild(b);
    });
  }

  function show(i) {
    var r = RELICS[i];
    [].forEach.call(document.querySelectorAll('#pick button'), function (b, k) {
      b.setAttribute('aria-selected', k === i ? 'true' : 'false');
    });
    document.querySelector('#name .ar').textContent = r.ar;
    document.querySelector('#name .en').textContent = r.en;
    document.querySelector('#name p').textContent = r.note;
    document.getElementById('load').style.display = 'block';

    if (dressed) { scene.remove(dressed.group); dressed = null; }
    cur = r;
    want = r.dist;
    spin = r.spin;

    var v = window.__BUILD || Date.now();
    fetch('assets/models/relic/' + r.k + '.fx.json?v=' + v)
      .then(function (x) { return x.json(); })
      .catch(function () { return {}; })
      .then(function (meta) {
        loader.load('assets/models/relic/' + r.k + '.glb?v=' + v, function (g) {
          var root = g.scene;
          /* stand it on the floor, whatever it was modelled around */
          var bb = new T.Box3().setFromObject(root);
          var c = new T.Vector3(); bb.getCenter(c);
          root.position.x -= c.x;
          root.position.z -= c.z;
          root.position.y -= bb.min.y;
          dressed = W.dressRelic(root, meta, r.k, scene);
          dressed.group.position.y = meta.up || 0;
          var bb2 = new T.Box3().setFromObject(root);
          target.set(0, (bb2.min.y + bb2.max.y) / 2 + (meta.up || 0), 0);
          document.getElementById('load').style.display = 'none';
        }, undefined, function (e) {
          document.getElementById('load').textContent = 'could not load ' + r.k;
        });
      });
  }

  function controls() {
    var down = false, lx = 0, ly = 0;
    var el = renderer.domElement;
    el.addEventListener('pointerdown', function (e) {
      down = true; lx = e.clientX; ly = e.clientY; el.setPointerCapture(e.pointerId);
    });
    el.addEventListener('pointermove', function (e) {
      if (!down) return;
      yaw -= (e.clientX - lx) * 0.006;
      pitch = Math.max(-0.45, Math.min(1.05, pitch + (e.clientY - ly) * 0.004));
      lx = e.clientX; ly = e.clientY;
      spin = 0;                       /* she has taken hold of it */
    });
    function up(e) { down = false; }
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
    el.addEventListener('wheel', function (e) {
      e.preventDefault();
      want = Math.max(0.7, Math.min(7.0, want + e.deltaY * 0.0016));
    }, { passive: false });
  }

  /* ONE STEP OF THE ROOM, and the camera is placed HERE rather than in the
     animation loop. It was in the loop, and requestAnimationFrame does not
     fire at all in a browser pane that is not being displayed - so the camera
     sat at the origin, the render pass drew nothing, and the whole frame was
     the single blit triangle at the end of the composer. A page that can only
     be driven by rAF cannot be checked. */
  /* THE CLOCK ONLY MOVES WHEN getDelta IS CALLED. step() read
     clock.elapsedTime, and a probe driving the page by calling step directly
     never touched getDelta - so t was frozen and nothing animated at all:
     no beat, no twinkle, no shed. Time is kept here instead. */
  var tNow = 0;
  function step(dt) {
    tNow += dt;
    var t = tNow;
    yaw += spin * dt;
    dist += (want - dist) * Math.min(1, dt * 4);
    var cp = Math.cos(pitch);
    cam.position.set(target.x + Math.sin(yaw) * dist * cp,
                     target.y + Math.sin(pitch) * dist + 0.10,
                     target.z + Math.cos(yaw) * dist * cp);
    cam.lookAt(target);
    if (dressed) dressed.tick(t, cam.position, dt);
    composer.render();
  }

  var lastRaf = 0;
  function frame() {
    requestAnimationFrame(frame);
    lastRaf = performance.now();
    step(Math.min(clock.getDelta(), 0.05));
  }
  W.relicTime = function () { return tNow; };

  /* the viewer is its own page, so it fetches its own build number */
  fetch('version.json?t=' + Date.now(), { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) { window.__BUILD = j.build; boot(); })
    .catch(function () { window.__BUILD = Date.now(); boot(); });

  /* a probe hook, so a shot can be taken without a pointer */
  W.relicView = function (i, o) {
    if (i !== undefined && i !== null) show(i);
    if (o) {
      if (o.yaw !== undefined) yaw = o.yaw;
      if (o.pitch !== undefined) pitch = o.pitch;
      if (o.dist !== undefined) { want = o.dist; dist = o.dist; }
      if (o.spin !== undefined) spin = o.spin;
    }
    return { yaw: yaw, pitch: pitch, dist: dist, loaded: !!dressed };
  };
  W.relicRenderer = function () { return renderer; };
  W.relicComposer = function () { return composer; };
  W.relicScene = function () { return { scene: scene, cam: cam, dressed: dressed,
                                        target: target }; };
  W.relicStep = function (n) {
    for (var i = 0; i < (n || 1); i++) step(0.033);
  };
})();
