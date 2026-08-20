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
    glow_edge: { col: 0xd84a90, emi: 0xff4d9e, str: 0.80, rough: 0.28 },
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
          /* not a glow slot: keep it, but make sure it is not shiny-black in
             a dark room - a relic seen by its own light needs a floor of
             ambient response */
          m.envMapIntensity = 2.6;
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
      tick: function (t, camPos) {
        if (motes) driveMotes(motes, t, camPos, group.position);
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
