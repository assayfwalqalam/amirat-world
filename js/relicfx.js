/* WHAT MAKES A RELIC GLOW.
   =================================================================
   The models carry the SHAPE and this carries the LIGHT, and the two are kept
   apart on purpose: the glTF exporter's emissive handling is not worth
   fighting, and everything about how bright a thing is wants tuning after you
   have looked at it, which means it must not require a rebuild in Blender.

   The contract is the material NAME. A part built onto a slot called glow_core
   or glow_edge or glow_gem comes out of the file with that name on it, and
   this turns it into an emissive material - given its colour, its strength and
   its own falloff here. Everything else is left as it was.

   Three things together make a thing read as radiating, and it needs all
   three:
     the surface       - emissive, so the bloom pass finds it
     the air around it - motes, drifting, so the light has something to be in
     the room          - a real point light, so what is NEAR it is lit too
   With only the first it is a bright sticker. With only the third it is a
   lamp. */
(function () {
  'use strict';
  var W = window.W = window.W || {};
  var T = window.THREE;

  /* how each named slot burns. Colour, how hard it burns, and how much of its
     own colour it keeps in its base - a gem is almost white-hot at the centre
     and a carved edge is not. */
  /* THE NUMBERS ARE LOW ON PURPOSE. Under ACES tone mapping anything much
     above 1 is carried toward white, so an emissive set bright enough to look
     bright on its own comes out as a white stripe with no colour left in it -
     which is what the first pass at the sabre's fuller did. The SURFACE is
     kept where its colour survives, and the BLOOM is what makes it read as
     radiating. That is also the honest division: a glowing thing is not a
     bright thing, it is a thing that puts light into the air around it. */
  var BURN = {
    glow_core: { col: 0xc4407e, emi: 0xff2f8c, str: 1.15, rough: 0.35 },
    glow_edge: { col: 0xd84a90, emi: 0xff4d9e, str: 0.62, rough: 0.28 },
    glow_gem:  { col: 0xe89ac8, emi: 0xff7ec4, str: 1.70, rough: 0.12 }
  };

  /* the palette the carpet's motes are drawn from - his five colours */
  var CARPET_COLS = [0xff77c8, 0xc98bff, 0x8ab6ff, 0xffffff, 0xffd98a];

  /* THE NAME THAT COMES OUT OF THE FILE IS NOT THE NAME THAT WENT IN.
     The slots are called glow_core and glow_edge in the generator, but the
     material Blender makes for one is called mat_glow_core, and that is what
     the glTF carries. Matching on the bare name found nothing, so nothing was
     ever turned emissive - and since the steel and the gold are metals with
     no environment to reflect, the whole relic rendered black on black and
     the frame came back a uniform 36 of 255. */
  function burnFor(name) {
    if (!name) return null;
    return BURN[name] || BURN[name.replace(/^mat_/, '')] || null;
  }

  /* AND A METAL WITH NOTHING TO REFLECT IS BLACK. There is no sky in the room
     these are shown in, on purpose, so one has to be made: a small vertical
     gradient, run through PMREM, standing in for the light a polished thing
     would be picking up off its surroundings. Without it, gold reads as coal. */
  var ENV = null;
  W.relicEnv = function (renderer) {
    if (ENV) return ENV;
    var S = 32, data = new Uint8Array(S * S * 4);
    for (var y = 0; y < S; y++) {
      var t = y / (S - 1);
      /* warm and low near the floor, cool and dim near the top - the room */
      /* Bright enough that a polished thing has something to be polished
         AGAINST. At a quarter of this the gold read as coal and the steel as
         a silhouette - a metal shows you its surroundings and almost nothing
         else, so if there are no surroundings there is no metal. */
      var r = 96 + 120 * (1 - t) + 40 * t;
      var g = 84 + 76 * (1 - t) + 48 * t;
      var b = 78 + 52 * (1 - t) + 86 * t;
      for (var x = 0; x < S; x++) {
        var i = (y * S + x) * 4;
        data[i] = r; data[i + 1] = g; data[i + 2] = b; data[i + 3] = 255;
      }
    }
    var tex = new T.DataTexture(data, S, S);
    tex.mapping = T.EquirectangularReflectionMapping;
    tex.needsUpdate = true;
    var pm = new T.PMREMGenerator(renderer);
    pm.compileEquirectangularShader();
    ENV = pm.fromEquirectangular(tex).texture;
    pm.dispose();
    tex.dispose();
    return ENV;
  };

  var moteTex = null;
  function moteTexture() {
    if (moteTex) return moteTex;
    var c = document.createElement('canvas');
    c.width = c.height = 64;
    var x = c.getContext('2d');
    var g = x.createRadialGradient(32, 32, 0, 32, 32, 31);
    g.addColorStop(0.00, 'rgba(255,255,255,1)');
    g.addColorStop(0.22, 'rgba(255,255,255,0.72)');
    g.addColorStop(0.55, 'rgba(255,255,255,0.16)');
    g.addColorStop(1.00, 'rgba(255,255,255,0)');
    x.fillStyle = g;
    x.fillRect(0, 0, 64, 64);
    moteTex = new T.CanvasTexture(c);
    moteTex.needsUpdate = true;
    return moteTex;
  }

  /* ------------------------------------------------------------ the motes
     One InstancedMesh for the whole swarm, so a hundred of them cost one draw
     call. They are billboards, re-aimed at the camera each frame, drifting on
     their own slow loops - no two on the same period, or the whole swarm
     pulses together and reads as a machine. */
  function makeMotes(spec, kind) {
    var n = spec.n || 24;
    var geo = new T.PlaneGeometry(1, 1);
    var mat = new T.MeshBasicMaterial({
      map: moteTexture(), transparent: true, depthWrite: false,
      blending: T.AdditiveBlending, toneMapped: false, opacity: 0.95,
      vertexColors: true
    });
    var mesh = new T.InstancedMesh(geo, mat, n);
    mesh.frustumCulled = false;
    var cols = new Float32Array(n * 3);
    var st = [];
    var c = new T.Color();
    for (var i = 0; i < n; i++) {
      /* the carpet takes his five colours; everything else stays in the pink
         it is radiating */
      if (kind === 'carpet') c.setHex(CARPET_COLS[i % CARPET_COLS.length]);
      else c.setHSL(0.90 + (i % 5) * 0.012, 0.85, 0.72);
      cols[i * 3] = c.r; cols[i * 3 + 1] = c.g; cols[i * 3 + 2] = c.b;
      st.push({
        a: Math.random() * 6.283,           /* where it is round the axis */
        r: (0.35 + Math.random() * 0.65),   /* how far out, as a fraction */
        y: Math.random(),                   /* where it is up the column */
        sp: 0.10 + Math.random() * 0.26,    /* how fast it goes round */
        bo: 0.25 + Math.random() * 0.75,    /* its own bob */
        bs: 0.5 + Math.random() * 1.4,
        sc: 0.012 + Math.random() * 0.026,
        ph: Math.random() * 6.283
      });
    }
    geo.setAttribute('color', new T.InstancedBufferAttribute(cols, 3));
    mesh.instanceColor = new T.InstancedBufferAttribute(cols, 3);
    return { mesh: mesh, st: st, spec: spec, dummy: new T.Object3D() };
  }

  function driveMotes(m, t, camPos, origin) {
    var sp = m.spec, d = m.dummy;
    for (var i = 0; i < m.st.length; i++) {
      var s = m.st[i];
      var a = s.a + t * s.sp;
      var rr = sp.r * s.r;
      var yy = sp.flat
        ? (sp.y + 0.04 + Math.abs(Math.sin(t * s.bs * 0.5 + s.ph)) * sp.h * s.bo)
        : (sp.y + s.y * sp.h + Math.sin(t * s.bs + s.ph) * 0.07);
      d.position.set(origin.x + Math.cos(a) * rr,
                     origin.y + yy,
                     origin.z + Math.sin(a) * rr);
      d.lookAt(camPos);
      var pulse = 0.72 + 0.28 * Math.sin(t * (1.3 + s.bs) + s.ph * 2.0);
      d.scale.setScalar(s.sc * pulse);
      d.updateMatrix();
      m.mesh.setMatrixAt(i, d.matrix);
    }
    m.mesh.instanceMatrix.needsUpdate = true;
  }

  /* ---------------------------------------------------------- the stones
     Sapphires, rubies and diamonds set in the white of the feathers.

     THEY ARE NOT IN THE MODEL. A gem baked into the mesh is a bump on a
     surface: it cannot twinkle on its own clock, it cannot follow the wing as
     it beats, and it certainly cannot be shed. So the generator writes out
     anchor points and they are made here - four hundred and fifty of them in
     ONE instanced mesh, which is one draw call for the lot.

     Each has its own period and its own phase, because a field of lights all
     breathing together is a string of fairy lights and not a field of stars. */
  /* Deep, because the bloom washes everything toward white and a stone that
     starts near white has nothing left to lose. */
  var GEM_COL = {
    sapphire: 0x2a5cff,
    ruby:     0xff1440,
    diamond:  0xeaf4ff
  };

  var gemGeo = null;
  function gemGeometry() {
    if (gemGeo) return gemGeo;
    /* an octahedron reads as a cut stone from any angle and costs 8 faces */
    gemGeo = new T.OctahedronGeometry(1, 0);
    /* AND IT NEEDS A COLOUR ATTRIBUTE OF ITS OWN. A material with
       vertexColors on defines USE_COLOR, and the shader then reads a `color`
       attribute the geometry does not have - so vColor comes out flat and the
       per-instance colour it is supposed to be multiplied by never shows.
       Every stone was white: no sapphire, no ruby. */
    var n = gemGeo.attributes.position.count;
    var ones = new Float32Array(n * 3);
    for (var i = 0; i < n * 3; i++) ones[i] = 1;
    gemGeo.setAttribute('color', new T.BufferAttribute(ones, 3));
    return gemGeo;
  }

  function makeGems(list, flap, scale) {
    scale = scale || 1.0;
    var n = list.length;
    /* AN EMISSIVE IS NOT MULTIPLIED BY THE INSTANCE COLOUR. Only the diffuse
       is - so a standard material with a white emissive bright enough to glow
       made every stone white however carefully each one had been tinted: no
       sapphire, no ruby, four hundred and fifty identical diamonds. A basic
       material's colour IS its output, and vColor and the instance colour
       both land on it, so the stone's own hue is what burns. */
    var mat = new T.MeshBasicMaterial({
      color: 0xffffff, vertexColors: true, toneMapped: false
    });
    var mesh = new T.InstancedMesh(gemGeometry(), mat, n);
    mesh.frustumCulled = false;
    var cols = new Float32Array(n * 3);
    var c = new T.Color();
    var st = [];
    for (var i = 0; i < n; i++) {
      var g = list[i];
      c.setHex(GEM_COL[g[3]] || 0xffffff);
      /* pushed past 1 on purpose: that is what the bloom threshold is looking
         for, and it is how a facet catches the light rather than merely being
         a coloured shape */
      /* over 1 so the bloom finds it, but not so far over that every channel
         clips and the hue is thrown away with the headroom */
      cols[i * 3] = c.r * 1.22; cols[i * 3 + 1] = c.g * 1.22;
      cols[i * 3 + 2] = c.b * 1.22;
      st.push({
        x: g[0], y: g[1], z: g[2],
        /* SET STONES, NOT CONFETTI - and the size is per relic, because a
           stone that reads correctly set in a wing two and a half metres
           across is a boulder hanging off a three-centimetre ring. */
        sc: (0.024 + (i % 7) * 0.0038) * scale,
        ph: (i * 2.39996) % 6.283,          /* the golden angle: no two align */
        sp: 1.1 + ((i * 37) % 100) / 100 * 2.4,
        spin: 0.4 + ((i * 53) % 100) / 100 * 1.1
      });
    }
    mesh.instanceColor = new T.InstancedBufferAttribute(cols, 3);
    return { mesh: mesh, st: st, flap: flap, dummy: new T.Object3D(),
             cols: cols };
  }

  /* HOW A WING BENDS. One formula, used in three places - the vertex shader
     that bends the feathers, the code that carries the gems with them, and
     the code that decides where a shed gem starts. If they ever disagree the
     stones come off the wing and hang in the air beside it. */
  function flapAngle(x, t, flap) {
    if (!flap) return 0;
    var d = Math.min(1, Math.abs(x) / (flap.span || 2.6));
    var beat = Math.sin(t * (flap.rate || 0.42) * 6.283);
    /* the stroke is not a sine: the downbeat is quicker than the recovery,
       which is what makes it read as effort rather than as a pendulum */
    beat = beat >= 0 ? Math.pow(beat, 0.7) : -Math.pow(-beat, 1.5);
    return (flap.amp || 0.30) * d * d * beat * (x < 0 ? -1 : 1);
  }
  W.flapAngle = flapAngle;

  function driveGems(G, t) {
    var d = G.dummy, st = G.st;
    for (var i = 0; i < st.length; i++) {
      var s = st[i];
      var a = flapAngle(s.x, t, G.flap);
      var ca = Math.cos(a), sa = Math.sin(a);
      d.position.set(s.x * ca - s.y * sa, s.x * sa + s.y * ca, s.z);
      d.rotation.set(t * s.spin, t * s.spin * 0.7, a);
      /* THE TWINKLE. A stone catches the light and loses it; the sharp peaks
         are what makes it read as a facet turning rather than as a bulb being
         dimmed, so the curve is pushed toward its top end. */
      var tw = 0.5 + 0.5 * Math.sin(t * s.sp + s.ph);
      d.scale.setScalar(s.sc * (0.42 + 1.05 * tw * tw));
      d.updateMatrix();
      G.mesh.setMatrixAt(i, d.matrix);
    }
    G.mesh.instanceMatrix.needsUpdate = true;
  }

  /* ------------------------------------------------------------ the beat
     THE WINGS BEND IN THE VERTEX SHADER, not on a skeleton. A rig would mean
     bones, weights, and a joined mesh cut back apart into fourteen pieces -
     for a motion that is one rotation whose angle grows with distance from
     the shoulder. Every vertex is turned about Z by that angle, which bends
     the whole span smoothly and costs nothing, and it is the SAME formula the
     stones are carried by, so the two can never drift apart.

     A wing that swings rigidly from the shoulder is a door. A real one bends
     along its length - the tip travels furthest and arrives last - which is
     why the angle goes with the SQUARE of the distance out. */
  function makeFlappable(mat, flap) {
    if (!mat || mat.__flap) return mat;
    mat.__flap = { value: 0 };
    mat.__span = { value: flap.span || 2.6 };
    mat.onBeforeCompile = function (sh) {
      sh.uniforms.uFlap = mat.__flap;
      sh.uniforms.uSpan = mat.__span;
      sh.vertexShader = 'uniform float uFlap;\nuniform float uSpan;\n' +
        sh.vertexShader.replace(
          '#include <begin_vertex>',
          [
            '#include <begin_vertex>',
            'float fd = min(1.0, abs(transformed.x) / uSpan);',
            'float fa = uFlap * fd * fd * sign(transformed.x);',
            'float fc = cos(fa), fs = sin(fa);',
            'transformed.xy = vec2(transformed.x * fc - transformed.y * fs,',
            '                      transformed.x * fs + transformed.y * fc);'
          ].join('\n'));
      /* the normals have to turn with it or the lighting stays where the
         wing used to be */
      sh.vertexShader = sh.vertexShader.replace(
        '#include <beginnormal_vertex>',
        [
          '#include <beginnormal_vertex>',
          'float nd = min(1.0, abs(position.x) / uSpan);',
          'float na = uFlap * nd * nd * sign(position.x);',
          'float nc = cos(na), ns = sin(na);',
          'objectNormal.xy = vec2(objectNormal.x * nc - objectNormal.y * ns,',
          '                       objectNormal.x * ns + objectNormal.y * nc);'
        ].join('\n'));
    };
    mat.needsUpdate = true;
    return mat;
  }

  /* --------------------------------------------------- what is let go of
     A shed stone, a falling petal, a mote left in the air behind a swing -
     all the same thing: something released at a point with a little sideways
     drift, which sinks slowly, turns, and fades out over its life. One
     instanced mesh per kind serves the lot, and a dead one is simply reused,
     so nothing is allocated after the first time. */
  function makeFall(geo, mat, cap) {
    var mesh = new T.InstancedMesh(geo, mat, cap);
    mesh.frustumCulled = false;
    mesh.count = cap;
    var cols = new Float32Array(cap * 3);
    for (var i = 0; i < cap * 3; i++) cols[i] = 1;
    mesh.instanceColor = new T.InstancedBufferAttribute(cols, 3);
    var pool = [];
    for (var k = 0; k < cap; k++) {
      pool.push({ live: 0, age: 0, life: 1, x: 0, y: -9999, z: 0,
                  vx: 0, vy: 0, vz: 0, sc: 0.02, spin: 0, ph: 0 });
    }
    return { mesh: mesh, pool: pool, cols: cols, dummy: new T.Object3D(),
             next: 0 };
  }

  function emit(F, x, y, z, opt) {
    opt = opt || {};
    var p = null;
    for (var i = 0; i < F.pool.length; i++) {
      var k = (F.next + i) % F.pool.length;
      if (!F.pool[k].live) { p = F.pool[k]; F.next = (k + 1) % F.pool.length; break; }
    }
    if (!p) return null;                    /* all in the air; drop this one */
    p.live = 1; p.age = 0;
    p.life = opt.life || 6.0;
    p.x = x; p.y = y; p.z = z;
    var sp = opt.spread === undefined ? 0.35 : opt.spread;
    p.vx = (Math.random() - 0.5) * sp;
    p.vz = (Math.random() - 0.5) * sp;
    p.vy = (opt.rise === undefined ? 0.10 : opt.rise) * (0.4 + Math.random());
    p.sc = (opt.size || 0.02) * (0.6 + Math.random() * 0.8);
    p.spin = (Math.random() - 0.5) * 3.0;
    p.ph = Math.random() * 6.283;
    if (opt.col && F.cols) {
      var i3 = F.pool.indexOf(p) * 3;
      F.cols[i3] = opt.col.r; F.cols[i3 + 1] = opt.col.g; F.cols[i3 + 2] = opt.col.b;
      F.mesh.instanceColor.needsUpdate = true;
    }
    return p;
  }

  function driveFall(F, dt, t) {
    var d = F.dummy, any = false;
    for (var i = 0; i < F.pool.length; i++) {
      var p = F.pool[i];
      if (!p.live) {
        d.position.set(0, -9999, 0);
        d.scale.setScalar(0.0001);
        d.updateMatrix();
        F.mesh.setMatrixAt(i, d.matrix);
        continue;
      }
      any = true;
      p.age += dt;
      if (p.age >= p.life) { p.live = 0; continue; }
      var u = p.age / p.life;
      /* SLOWLY. It is light coming off a thing, not gravel: it drifts down at
         a walking pace and the air keeps taking it sideways the whole way. */
      p.vy -= 0.16 * dt;
      p.vy = Math.max(p.vy, -0.30);
      p.x += (p.vx + Math.sin(t * 1.3 + p.ph) * 0.09) * dt;
      p.z += (p.vz + Math.cos(t * 1.1 + p.ph * 1.7) * 0.09) * dt;
      p.y += p.vy * dt;
      d.position.set(p.x, p.y, p.z);
      d.rotation.set(t * p.spin, t * p.spin * 0.8, p.ph);
      /* it comes up quickly, holds, and goes out slowly */
      var fade = Math.min(1, u * 8) * (1 - u) * (1 - u);
      var tw = 0.65 + 0.35 * Math.sin(t * 6.0 + p.ph * 3.0);
      d.scale.setScalar(p.sc * fade * (0.7 + 0.5 * tw));
      d.updateMatrix();
      F.mesh.setMatrixAt(i, d.matrix);
    }
    F.mesh.instanceMatrix.needsUpdate = true;
    return any;
  }

  W.moteTexture = moteTexture;
  W.gemGeometry = gemGeometry;
  W.makeFall = makeFall;
  W.fallEmit = emit;
  W.fallDrive = driveFall;

  /* --------------------------------------------------------------- dress
     Give a loaded relic its light. Returns a handle with a tick(). */
  W.dressRelic = function (root, meta, kind, scene) {
    meta = meta || {};
    var lit = [];
    root.traverse(function (o) {
      if (!o.isMesh || !o.material) return;
      var ms = Array.isArray(o.material) ? o.material : [o.material];
      var out = ms.map(function (m) {
        var b = burnFor(m.name);
        if (!b) {
          /* NOT A GLOW SLOT. The environment was turned up hard on everything
             so that the gold and the steel would have something to reflect -
             and a rough non-metal reflects it too, as flat white light over
             the whole surface. Every petal on the carpet's border and every
             feather in the wings came out white however carefully it had been
             coloured. Only metal gets the bright room; matte things get the
             ordinary one. */
          m.envMapIntensity = (m.metalness !== undefined && m.metalness > 0.5)
            ? 2.6 : 0.85;
          return m;
        }
        var e = new T.MeshStandardMaterial({
          color: b.col, emissive: b.emi, emissiveIntensity: b.str,
          roughness: b.rough, metalness: 0.0, toneMapped: true
        });
        e.name = m.name;
        lit.push(e);
        return e;
      });
      o.material = Array.isArray(o.material) ? out : out[0];
    });

    var group = new T.Group();
    group.add(root);

    /* the stones, and the beat that carries them */
    var gems = null, flapMats = [];
    if (meta.gems && meta.gems.length) {
      gems = makeGems(meta.gems, meta.flap, meta.gemScale);
      /* ON THE MODEL, not beside it. The viewer and the world both shift the
         loaded root so the relic stands on the floor; anything added to the
         group instead of to the root does not get that shift and ends up
         hanging wherever the model happened to be authored. */
      root.add(gems.mesh);
    }
    if (meta.flap) {
      root.traverse(function (o) {
        if (!o.isMesh || !o.material) return;
        var ms2 = Array.isArray(o.material) ? o.material : [o.material];
        ms2.forEach(function (mm) { flapMats.push(makeFlappable(mm, meta.flap)); });
      });
    }

    /* WHAT THE BEAT SHEDS. On the downstroke of every wingbeat a handful of
       stones come away and sink, still turning, still catching the light. */
    var shed = null;
    if (meta.gems && meta.gems.length) {
      shed = makeFall(gemGeometry(), new T.MeshBasicMaterial({
        color: 0xffffff, vertexColors: true, toneMapped: false,
        transparent: true, depthWrite: false
      }), 64);
      root.add(shed.mesh);
    }

    /* the air round it */
    var motes = null;
    if (meta.motes) {
      motes = makeMotes(meta.motes, kind);
      group.add(motes.mesh);
    }

    /* and the room */
    var lights = [];
    (meta.lights || []).forEach(function (L) {
      var pl = new T.PointLight(new T.Color(L.c || '#ff6fb2'), L.p || 1.2,
                                L.r || 6.0, 2);
      pl.position.set(L.x || 0, L.y || 0.4, L.z || 0);
      group.add(pl);
      lights.push({ l: pl, base: L.p || 1.2 });
    });

    (scene || W.scene).add(group);

    return {
      group: group,
      motes: motes,
      lights: lights,
      lit: lit,
      gems: gems,
      shed: shed,
      tick: function (t, camPos, dt) {
        dt = dt || 0.016;
        if (motes) driveMotes(motes, t, camPos, group.position);
        if (gems) driveGems(gems, t);
        if (flapMats.length && meta.flap) {
          var a = 0;
          var beat = Math.sin(t * (meta.flap.rate || 0.42) * 6.283);
          beat = beat >= 0 ? Math.pow(beat, 0.7) : -Math.pow(-beat, 1.5);
          a = (meta.flap.amp || 0.30) * beat;
          for (var fi = 0; fi < flapMats.length; fi++) {
            if (flapMats[fi].__flap) flapMats[fi].__flap.value = a;
          }
          /* let a few go at the bottom of each downstroke */
          if (shed && gems) {
            var phase = (t * (meta.flap.rate || 0.42)) % 1.0;
            if (this.__last === undefined) this.__last = phase;
            if (phase < this.__last) {            /* the cycle turned over */
              for (var q = 0; q < 5; q++) {
                var g0 = gems.st[(Math.random() * gems.st.length) | 0];
                var ga = flapAngle(g0.x, t, meta.flap);
                var gc = Math.cos(ga), gs2 = Math.sin(ga);
                var i3 = gems.st.indexOf(g0) * 3;
                emit(shed,
                     g0.x * gc - g0.y * gs2,
                     g0.x * gs2 + g0.y * gc,
                     g0.z,
                     { life: 6.5, size: 0.022, spread: 0.14, rise: 0.02,
                       col: { r: gems.cols[i3], g: gems.cols[i3 + 1],
                              b: gems.cols[i3 + 2] } });
              }
            }
            this.__last = phase;
          }
        }
        if (shed) driveFall(shed, dt, t);
        /* the light breathes, slowly and by a little - a relic that pulses
           hard reads as a machine with a fault */
        var b = 0.90 + 0.10 * Math.sin(t * 0.9) + 0.04 * Math.sin(t * 2.3);
        for (var i = 0; i < lights.length; i++) {
          lights[i].l.intensity = lights[i].base * b;
        }
        for (var k = 0; k < lit.length; k++) {
          var m2 = lit[k];
          if (m2.__b === undefined) m2.__b = m2.emissiveIntensity;
          m2.emissiveIntensity = m2.__b * (0.88 + 0.12 * Math.sin(t * 1.4 + k));
        }
      }
    };
  };

  W.RELIC_BURN = BURN;
})();
