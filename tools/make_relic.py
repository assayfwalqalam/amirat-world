# -*- coding: utf-8 -*-
"""The relics of the Rawda.

    blender --background --python tools/make_relic.py -- sabre assets/models/relic/sabre.glb assets

Five things that are meant to look legendary rather than lived-in, so they are
built to a different rule from the props: the props exist to be walked past and
these exist to be looked AT, which means the shapes have to hold up at half a
metre and the glow has to come from the object rather than be painted on it.

HOW THE GLOW WORKS. Nothing here is emissive in Blender - the glTF exporter's
emissive handling is not worth fighting, and the engine has an UnrealBloomPass
already. Instead every part is tagged onto a named SLOT, and the engine reads
the material names: anything called glow_* is turned into an emissive material
at load, given its colour and strength there, and lit by a real point light.
So the model carries the SHAPE and the ENGINE carries the light, and the two
can be tuned without rebuilding either.

Slots used: steel gold wood grip cloth feather petal glow_core glow_edge
            glow_gem
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "sabre"
OUT = argv[1] if len(argv) > 1 else (KIND + ".glb")
ASSETS = argv[2] if len(argv) > 2 else "assets"
random.seed(sum(ord(c) for c in KIND) * 7919)

scene = bpy.context.scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for x in list(blk):
        blk.remove(x)

parts = []
SLOTS = []


def slot(ob, name):
    key = "mat_" + name
    m = bpy.data.materials.get(key)
    if m is None:
        m = bpy.data.materials.new(key)
        m.use_nodes = True
        SLOTS.append(name)
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


# ------------------------------------------------------------- primitives
def keep(ob):
    parts.append(ob)
    return ob


def box(sx, sy, sz, loc, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.active_object
    ob.scale = (sx / 2, sy / 2, sz / 2)
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    return keep(ob)


def cyl(r1, r2, h, loc, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=h,
                                    vertices=verts, location=loc)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    return keep(ob)


def sphere(r, loc, seg=20, ring=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg,
                                         ring_count=ring, location=loc)
    return keep(bpy.context.active_object)


def torus(rmaj, rmin, loc, seg=24, minor=10, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=rmaj, minor_radius=rmin,
                                     major_segments=seg, minor_segments=minor,
                                     location=loc)
    ob = bpy.context.active_object
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(rotation=True)
    return keep(ob)


def lathe(profile, segments=24, name="v"):
    """spin a silhouette round Z"""
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    for i in range(len(vs) - 1):
        bm.edges.new((vs[i], vs[i + 1]))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], axis=(0, 0, 1),
                   cent=(0, 0, 0), dvec=(0, 0, 0), angle=math.pi * 2,
                   steps=segments, use_merge=True)
    bm.to_mesh(me)
    bm.free()
    return keep(ob)


def loft(rings, close=True, cap_a=True, cap_b=True, name="loft"):
    """Build a tube from a list of rings, each a list of the SAME number of
    (x, y, z) points. This is how every blade, quillon and feather here is
    made: a section is written once and then carried along a path, which is
    the only way to get a shape that tapers and curves at the same time and
    still closes."""
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    grid = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for i in range(len(rings) - 1):
        for j in range(n):
            k = (j + 1) % n
            if not close and k == 0:
                continue
            try:
                bm.faces.new((grid[i][j], grid[i][k], grid[i + 1][k], grid[i + 1][j]))
            except ValueError:
                pass
    if cap_a and close:
        try:
            bm.faces.new(list(reversed(grid[0])))
        except ValueError:
            pass
    if cap_b and close:
        try:
            bm.faces.new(grid[-1])
        except ValueError:
            pass
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    return keep(ob)


def jitter(ob, amt):
    for v in ob.data.vertices:
        v.co.x += random.uniform(-amt, amt)
        v.co.y += random.uniform(-amt, amt)
        v.co.z += random.uniform(-amt, amt)


# =========================================================== THE SABRE
def build_sabre():
    """A saif: a curved blade, a cross guard, a bound grip and a round pommel.
    It stands point-up so it can be shown on a stand, and every piece is
    joined to the next - the tang runs the whole way through, which is what
    "nothing floating out" means on a sword."""
    L = 0.96                     # blade length
    CURVE = 0.52                 # how far round the arc it bends, in radians
    RAD = L / CURVE              # radius of the spine's arc

    # THE SECTION, written once: half-thickness as you go from the spine
    # (u = 0) to the edge (u = 1). The dip in the middle is the fuller - the
    # groove down the flat of the blade that takes weight out without taking
    # stiffness with it.
    SECT = [(0.00, 0.50), (0.06, 0.50), (0.19, 0.43), (0.31, 0.27),
            (0.50, 0.23), (0.67, 0.33), (0.87, 0.19), (1.00, 0.03)]

    def spine_at(t):
        """where the back of the blade is, and which way is across it.
        A SWORD STANDS. The first version ran the blade along +X with a
        little rise in Z, so the whole thing lay on its side and read as a
        hairline seen end-on. The length goes UP now and the curve bends it
        sideways, which is also the right way round for the edge: the bend is
        toward +X and the edge is on the outside of the bend, where a sabre's
        edge is."""
        ang = CURVE * t
        sx = RAD * (1.0 - math.cos(ang))
        sz = RAD * math.sin(ang)
        # across the blade, from the spine toward the edge
        return sx, sz, math.cos(ang), -math.sin(ang)

    def blade_ring(t, wid, thk):
        """THE BLADE IS CENTRED ON THE GRIP'S AXIS. The section runs u = 0 at
        the spine to u = 1 at the edge, and it was laid out from the axis
        OUTWARD - so the whole blade sat on one side of the line the grip and
        the pommel are on, and at the guard it looked bolted to the edge of
        the hilt rather than growing out of the middle of it. Half a width is
        taken off, which puts the spine on one side of the centre and the edge
        on the other, where they belong."""
        sx, sz, ax, az = spine_at(t)
        pts = []
        for (u, hv) in SECT:
            o = (u - 0.5) * wid
            pts.append((sx + ax * o, +hv * thk, sz + az * o))
        for (u, hv) in reversed(SECT[1:-1]):
            o = (u - 0.5) * wid
            pts.append((sx + ax * o, -hv * thk, sz + az * o))
        return pts

    STEPS = 30
    rings = []
    for i in range(STEPS + 1):
        t = i / STEPS
        # width holds most of the way and then runs out into the point
        wid = 0.070 * (1.0 - 0.08 * t) * (1.0 - smooth(0.88, 1.0, t) * 0.95)
        thk = 0.0125 * (1.0 - 0.40 * t)
        rings.append(blade_ring(t, max(wid, 0.0018), max(thk, 0.0014)))
    slot(loft(rings, name="blade"), "steel")

    # THE LIGHT IN THE FULLER. A ribbon lying in the groove, a hair proud of
    # its floor, following the same path - so the glow is IN the blade and
    # not a sticker on the side of it.
    for side in (1, -1):
        gr = []
        for i in range(STEPS + 1):
            t = i / STEPS
            wid = 0.070 * (1.0 - 0.08 * t) * (1.0 - smooth(0.88, 1.0, t) * 0.95)
            thk = 0.0125 * (1.0 - 0.40 * t)
            sx, sz, ax, az = spine_at(t)
            ring = []
            for u in (0.34, 0.64):
                o = (u - 0.5) * wid
                for dv in (0.0018, -0.0018):
                    ring.append((sx + ax * o,
                                 side * (0.235 * thk + 0.0011) + dv,
                                 sz + az * o))
            gr.append([ring[0], ring[1], ring[3], ring[2]])
        slot(loft(gr, name="fuller%d" % side), "glow_edge")

    # THE SHOULDER AND THE GUARD. The blade sits into a collar, the collar
    # into the quillons, and the quillons carry langets that grip the blade -
    # so there is no join anywhere that is only two faces touching.
    slot(cyl(0.031, 0.026, 0.030, (0, 0, -0.015), verts=20), "gold")
    q = []
    QN = 16
    for i in range(QN + 1):
        t = i / QN
        a = (t - 0.5) * 2.0                       # -1 .. 1 across the guard
        x = a * 0.135
        z = -0.050 - 0.042 * (1.0 - math.cos(a * 1.35))   # the droop
        r = 0.023 * (1.0 - 0.58 * abs(a)) + 0.007
        ring = []
        for k in range(10):
            th = k * math.pi * 2 / 10
            ring.append((x, math.cos(th) * r, z + math.sin(th) * r * 0.72))
        q.append(ring)
    slot(loft(q, name="quillon"), "gold")
    for s in (-1, 1):
        slot(sphere(0.021, (s * 0.150, 0, -0.076), seg=16, ring=10), "gold")
    # langets down the flat of the blade
    for s in (-1, 1):
        slot(box(0.044, 0.016, 0.070, (0, s * 0.0075, 0.006)), "gold")

    # THE GRIP: waisted, and bound in a spiral all the way down its length
    slot(lathe([(0.000, -0.062), (0.021, -0.064), (0.024, -0.078),
                (0.021, -0.108), (0.019, -0.140), (0.021, -0.172),
                (0.024, -0.196), (0.021, -0.208), (0.000, -0.210)],
               segments=20, name="grip"), "grip")
    TURNS, BN = 9, 11
    band = []
    for i in range(TURNS * BN + 1):
        t = i / (TURNS * BN)
        z = -0.070 - t * 0.130
        rr = 0.0215 + 0.0035 * math.cos(t * math.pi * 2 - math.pi)
        th = t * TURNS * math.pi * 2
        cx, cy = math.cos(th), math.sin(th)
        ring = []
        for k in range(6):
            p = k * math.pi * 2 / 6
            ring.append((cx * (rr + math.cos(p) * 0.0032),
                         cy * (rr + math.cos(p) * 0.0032),
                         z + math.sin(p) * 0.0042))
        band.append(ring)
    slot(loft(band, name="binding"), "gold")

    # THE POMMEL: round, as he asked, with a collar under it and a small
    # finial on top where the tang is peened over.
    slot(cyl(0.024, 0.028, 0.014, (0, 0, -0.216), verts=20), "gold")
    slot(sphere(0.040, (0, 0, -0.250), seg=24, ring=16), "gold")
    # a fluted ring set INTO the pommel rather than a band strapped round it
    slot(torus(0.0355, 0.0075, (0, 0, -0.250), seg=26, minor=9), "glow_core")
    slot(cyl(0.011, 0.008, 0.016, (0, 0, -0.290), verts=12), "gold")

    return {"lights": [{"x": 0, "y": 0.30, "z": 0, "c": "#ff5fa8", "p": 1.5,
                        "r": 6.0}],
            "motes": {"n": 22, "r": 0.14, "h": 1.15, "y": 0.20},
            "up": 0.34}


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / max(b - a, 1e-6)))
    return t * t * (3.0 - 2.0 * t)


# =========================================================== THE CARPET
def build_carpet():
    GEMS = []
    KINDS = ("rose", "diamond", "sapphire", "ruby", "amethyst")

    """A carpet is a plane, and a plane is the hardest thing to make look like
    anything. This one is given a real pile - it sags between where it touches
    and lifts at the corners the way a rug that has been walked on does - a
    knotted border in relief, and a field of small raised medallions that the
    engine lights from within."""
    W, D = 2.05, 1.35
    NX, NY = 36, 24
    rings = []
    verts = []
    for j in range(NY + 1):
        row = []
        for i in range(NX + 1):
            u = i / NX - 0.5
            v = j / NY - 0.5
            # the lift: corners rise, the middle lies flat
            lift = (abs(u) * 2) ** 3 * 0.035 + (abs(v) * 2) ** 3 * 0.028
            ripple = (math.sin(u * 7.1) * math.cos(v * 5.3)) * 0.004
            row.append((u * W, v * D, 0.012 + lift + ripple))
        verts.append(row)
    me = bpy.data.meshes.new("field")
    ob = bpy.data.objects.new("field", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    grid = [[bm.verts.new(p) for p in row] for row in verts]
    for j in range(NY):
        for i in range(NX):
            bm.faces.new((grid[j][i], grid[j][i + 1],
                          grid[j + 1][i + 1], grid[j + 1][i]))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    sol = ob.modifiers.new("s", 'SOLIDIFY')
    sol.thickness = 0.016
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=sol.name)
    slot(keep(ob), "cloth")

    # the border: a raised guard band all the way round, in two runs
    # the guard stripes, in relief. Only the INNER one is lit - two burning
    # frames one inside the other was most of why it read as a light fitting.
    for k, inset in enumerate((0.040, 0.108)):
        w, d = W - inset * 2, D - inset * 2
        for (sx, sy, lx, ly) in ((0, 1, w, 0.022), (0, -1, w, 0.022),
                                 (1, 0, 0.022, d), (-1, 0, 0.022, d)):
            b = box(lx, ly, 0.009,
                    (sx * (w / 2), sy * (d / 2), 0.030 + k * 0.003))
            slot(b, "gold" if k == 0 else "glow_edge")

    # THE LIGHT IN THE WEAVE. Forty lit bosses over a rug this size turned it
    # into a lightbox with dots on it - the design does the work now and these
    # only pick out where the rosettes already are. A dozen, small, and only on
    # the lattice crossings.
    for j in range(3):
        for i in range(4):
            x = (i / 3.0 - 0.5) * (W - 0.62)
            y = (j / 2.0 - 0.5) * (D - 0.56)
            r = 0.020 if (i + j) % 2 == 0 else 0.014
            b = lathe([(0.0, 0.0), (r * 0.7, 0.004), (r, 0.012),
                       (r * 0.6, 0.020), (0.0, 0.024)], segments=12,
                      name="boss")
            b.location = (x, y, 0.031)
            GEMS.append([round(x, 4), 0.049, round(-y, 4),
                         KINDS[(i + j) % len(KINDS)]])
            bpy.context.view_layer.objects.active = b
            b.select_set(True)
            bpy.ops.object.transform_apply(location=True)
            b.select_set(False)
            slot(b, "glow_core" if (i + j) % 2 == 0 else "glow_gem")
    # ------------------------------------------------- flowers on the border
    # THE PATTERN IS WOVEN, SO IT IS FLAT. A carpet's design is dye in wool
    # and it lies in the plane however good the drawing is - which is why the
    # border read as printed. These are the same flowers the staff carries,
    # laid round the frame in RELIEF, so the light rakes across them and the
    # border has a thickness the eye can find. Fifty-two of them, close
    # enough to touch, because a border with a flower every foot is a fence.
    def blossom(bx2, by2, bz2, sc2, face2, tilt2, gems2):
        """one five-petal flower lying on the mat, opened toward the eye"""
        for pi2 in range(5):
            pa2 = face2 + pi2 * math.pi * 2 / 5 + random.uniform(-0.14, 0.14)
            z2 = random.uniform(0.88, 1.12) * sc2
            pl2 = lathe([(0.0, 0.0), (0.010, 0.002), (0.017, 0.007),
                         (0.019, 0.014), (0.011, 0.019), (0.0, 0.020)],
                        segments=8, name="rpetal")
            pl2.scale = (z2, z2 * 1.7, z2 * 0.62)
            pl2.rotation_euler = (tilt2, 0, pa2)
            pl2.location = (bx2 + math.cos(pa2) * 0.016 * sc2,
                            by2 + math.sin(pa2) * 0.016 * sc2, bz2)
            bpy.context.view_layer.objects.active = pl2
            pl2.select_set(True)
            bpy.ops.object.transform_apply(location=True, rotation=True,
                                           scale=True)
            pl2.select_set(False)
            slot(pl2, "petal")
        # THE HEART OF IT IS A STAR. It was a small lit ball, which is a bead
        # - and a border of beads is exactly what "bland" means. The engine
        # sets a twinkling star here instead, on its own clock like every
        # other stone in the set, so the border catches the light the way the
        # wings do. Nothing is modelled: only the point is written down.
        GEMS.append([round(bx2, 4), round(bz2 + 0.006 * sc2, 4),
                     round(-by2, 4), KINDS[gems2 % len(KINDS)]])

    # walk the border and set one down every so often, alternating which side
    # of the band it sits on so the run is a garland and not a queue
    BW, BD = W - 0.150, D - 0.150          # the middle of the main border
    per_x, per_y = 16, 10
    ring_pts = []
    for i in range(per_x):
        t2 = (i + 0.5) / per_x - 0.5
        ring_pts.append((t2 * BW, +BD / 2))
        ring_pts.append((t2 * BW, -BD / 2))
    for j in range(per_y):
        t2 = (j + 0.5) / per_y - 0.5
        ring_pts.append((+BW / 2, t2 * BD))
        ring_pts.append((-BW / 2, t2 * BD))
    gi2 = 0
    for (k2, (fx2, fy2)) in enumerate(ring_pts):
        # a little in or out of the band, and never twice the same size
        off = 0.020 if (k2 % 2 == 0) else -0.020
        nx2 = 1.0 if abs(fx2) > abs(fy2) else 0.0
        fx3 = fx2 + off * nx2 * (1 if fx2 > 0 else -1)
        fy3 = fy2 + off * (1 - nx2) * (1 if fy2 > 0 else -1)
        blossom(fx3, fy3, 0.033,
                random.uniform(0.86, 1.20),
                random.uniform(0, 6.283),
                random.uniform(0.10, 0.30), gi2)
        gi2 += 1

    # and a smaller run of them inside the guard stripe, so the field is not
    # cut off from the border by a hard line
    for k2 in range(20):
        a2 = k2 * math.pi * 2 / 20 + 0.3
        blossom(math.cos(a2) * (W * 0.315), math.sin(a2) * (D * 0.300), 0.033,
                random.uniform(0.55, 0.78), random.uniform(0, 6.283),
                random.uniform(0.08, 0.24), gi2)
        gi2 += 1

    # NO RAISED MEDALLION. There was a dome here, over the medallion that is
    # already woven into the carpet, and it was wrong either way it was tried:
    # lit, it burned out the whole centre - design, field and all; unlit, it
    # is a flat dark disc laid over the best part of the drawing. The woven
    # one was always the better medallion. The relief on this carpet is the
    # flowers and the guard stripes, and the middle is left to be read.

    # The light was directly overhead at 55 cm with a reach of seven metres,
    # which lit the rug's own face harder than anything else in the room. It
    # sits lower and reaches less: what it is for is the FLOOR round the rug,
    # so the carpet is seen to be spilling light rather than emitting it.
    # A POINT LIGHT 25 CM OVER A FLAT RUG BLOWS THE MIDDLE OF IT OUT. Falloff
    # is inverse-square, so at that range the irradiance on the pile is about
    # nine - every flower on the border rendered white however carefully its
    # petals had been coloured, and the medallion with them. It hangs well
    # clear now: the same amount of light reaching the carpet, spread evenly
    # over it rather than dumped on its centre.
    return {"lights": [{"x": 0, "y": 1.45, "z": 0, "c": "#ffa8d4", "p": 0.85,
                        "r": 5.2}],
            "motes": {"n": 46, "r": 1.05, "h": 0.85, "y": 0.06, "flat": 1},
            "gems": GEMS,
            # smaller than the wings' by a long way: a star has to be read
            # against the flower it is the heart OF, not instead of it
            "gemScale": 0.16,
            "up": 0.0}


# =========================================================== THE WINGS
def build_wings():
    """DRAGON WINGS, FEATHERED - from his reference picture, named so it
    cannot drift:

      - the leading edge is an ARM: it rises from the shoulder to a KNUCKLE
        at ~40% of the span, with a thumb-spike at the joint, then runs as
        the longest FINGER out to the far tip;
      - four more FINGER RAYS fan from the knuckle, each shorter and steeper
        than the last, the innermost pointing almost straight down;
      - the trailing edge is SCALLOPED: a concave arc between every pair of
        finger tips, so every tip stands out as a point - the one thing every
        wing in his picture shares;
      - a dragon's membrane fills the panels between the fingers; here the
        fill is FEATHERS - overlapping rows running down each panel, the
        outer row's tips tracing the scallop - because his order was dragon
        IN SHAPE, "but feathers and filled with it".

    Two planes a side (main + one behind at 4/5 scale) so the wing has depth
    without becoming the old seven-layer shell.
    """
    GEMS = []
    KINDS = ("rose", "sapphire", "diamond", "ruby", "amethyst")
    gi = 0

    def smooth(a, b, x):
        t = max(0.0, min(1.0, (x - a) / max(b - a, 1e-6)))
        return t * t * (3.0 - 2.0 * t)

    S0 = 2.9
    LAYERS = ((0.0, 1.00, 0.0), (0.14, 0.80, 0.10))    # pitch, scale, y-shift

    for side in (1, -1):
        for (li, (pitch, sc, yoff)) in enumerate(LAYERS):
            S = S0 * sc
            rj = random.Random(li * 613 + (11 if side > 0 else 5))

            def xf(x, y, z):
                # +y in wing-local space means PROUD OF THE FACE THE VIEWER
                # SEES. Blender +y exports to glTF -z, and the viewer camera
                # sits at +z: three renders in a row had a complete plumage
                # hidden BEHIND the membrane because this sign was wrong.
                x2 = x * math.cos(pitch) - z * math.sin(pitch)
                z2 = x * math.sin(pitch) + z * math.cos(pitch)
                return (side * (x2 + 0.10), -y + yoff + li * 0.06, z2 + 0.42)

            # the skeleton, jittered so no two layers or sides are twins
            # the rays SPREAD, and the whole frame is z-compressed: his
            # reference wing is about twice as wide as it is tall. The first
            # cut dropped the fan to the floor and each wing read as a
            # hanging curtain.
            ZS = 0.74
            K = (0.34 * S, ZS * 0.30 * S * rj.uniform(0.96, 1.05))
            TIPS = []
            for (tx, tz) in ((1.00, 0.02), (0.94, -0.26), (0.80, -0.50),
                             (0.58, -0.68), (0.34, -0.78)):
                TIPS.append((tx * S * rj.uniform(0.97, 1.03),
                             ZS * tz * S * rj.uniform(0.95, 1.06)))
            BODY = (0.05 * S, ZS * -0.42 * S)

            def bulge(t):
                """the wing has camber: proud in the middle, flat at edges"""
                return 0.05 * S * math.sin(math.pi * min(1.0, t))

            # THE ARM: shoulder up to the knuckle - a stacked tube with a
            # slight arch, so the leading edge reads as bone under cover
            NA = 8
            arm = []
            for i in range(NA + 1):
                t = i / float(NA)
                ax = K[0] * t
                az = K[1] * math.sin(t * math.pi / 2) + 0.02 * S * math.sin(t * 6.0)
                r = S * (0.050 - 0.022 * t)
                ring = []
                for q in range(7):
                    a = q / 6.0 * 2 * math.pi
                    ring.append(xf(ax, math.cos(a) * r,
                                   az + math.sin(a) * r))
                arm.append(ring)
            slot(loft(arm, close=True, cap_a=True, cap_b=True,
                      name="arm%d" % li), "feather")

            # THE CANOPY: one ruled sheet per finger panel, its outer edge
            # pulled in between the tips - the scallop is IN the surface,
            # not painted on
            def panel_pt(A, B, w, v):
                px = K[0] + v * ((1 - w) * (A[0] - K[0]) + w * (B[0] - K[0]))
                pz = K[1] + v * ((1 - w) * (A[1] - K[1]) + w * (B[1] - K[1]))
                return px, pz

            EDGES = list(TIPS) + [BODY]
            for k in range(len(EDGES) - 1):
                A, B = EDGES[k], EDGES[k + 1]
                rows = []
                NW, NV = 6, 7
                for iv in range(NV + 1):
                    v = iv / float(NV)
                    ring = []
                    for iw in range(NW + 1):
                        w = iw / float(NW)
                        vmax = 1.0 - 0.15 * math.sin(math.pi * w) \
                            * rj.uniform(0.9, 1.1)
                        px, pz = panel_pt(A, B, w, v * vmax)
                        ring.append(xf(px, bulge(v) * (1 - 0.6 * abs(w - 0.5)),
                                       pz))
                    rows.append(ring)
                can = loft(rows, close=False, cap_a=False, cap_b=False,
                           name="pan%d_%d" % (li, k))
                sol = can.modifiers.new("s", 'SOLIDIFY')
                sol.thickness = 0.016
                bpy.context.view_layer.objects.active = can
                bpy.ops.object.modifier_apply(modifier=sol.name)
                # the canopy is the pale pink UNDERLAYER everywhere; the
                # white plumage tiles over it
                slot(can, "feather_in")

            def feather(x0, z0, ang, L, wid, proud, slname, sag=0.06):
                """one feather card: tent section, full width to 60% then an
                ellipse tip - rooted at (x0,z0), pointing along ang"""
                ex, ez = math.sin(ang), -math.cos(ang)
                px2, pz2 = ez, -ex
                NR = 6
                rings = []
                for q in range(NR + 1):
                    ft = q / float(NR)
                    if ft < 0.60:
                        hw = wid * 0.5 * (0.62 + 0.38 * smooth(0.0, 0.25, ft))
                    else:
                        e = (ft - 0.60) / 0.40
                        hw = wid * 0.5 * math.sqrt(max(0.0, 1.0 - e * e))
                    hw = max(hw, 0.0015)
                    cx0 = x0 + ex * L * ft
                    cz0 = z0 + ez * L * ft - sag * L * ft * ft
                    rg = []
                    for (mu, my) in ((1.0, 0.0), (0.30, 0.007),
                                     (-0.30, 0.007), (-1.0, 0.0)):
                        rg.append(xf(cx0 + px2 * hw * mu, proud + my,
                                     cz0 + pz2 * hw * mu))
                    rings.append(rg)
                slot(loft(rings, name="f"), slname)

            # THE FINGER RIDGES: rows of small coverts marching down every
            # ray, slightly proud - the dark ribs of his picture, feathered
            for (k, T) in enumerate(TIPS):
                fl = math.hypot(T[0] - K[0], T[1] - K[1])
                ang = math.atan2(T[0] - K[0], -(T[1] - K[1]))
                n = 7 - k // 2
                for i in range(n):
                    t = (i + 0.5) / n
                    fx0 = K[0] + (T[0] - K[0]) * t
                    fz0 = K[1] + (T[1] - K[1]) * t + 0.012
                    L = fl * 0.24 * (1.0 - 0.35 * t) * rj.uniform(0.9, 1.1)
                    feather(fx0, fz0, ang + rj.uniform(-0.06, 0.06), L,
                            L * 0.34, bulge(t) + 0.030 + 0.004 * (i % 2),
                            "feather", sag=0.03)
                if li == 0 and k < 4:
                    mx, my, mz = xf(K[0] + (T[0] - K[0]) * 0.30,
                                    bulge(0.3) + 0.07,
                                    K[1] + (T[1] - K[1]) * 0.30)
                    GEMS.append([round(mx, 4), round(mz, 4),
                                 round(-my - 0.04, 4), KINDS[gi % 5]])
                    gi += 1

            # THE PANEL FILL: rows of feathers running down each panel, the
            # outermost row longest so its tips trace the scallop arc
            for k in range(len(EDGES) - 1):
                A, B = EDGES[k], EDGES[k + 1]
                span = math.hypot(B[0] - A[0], B[1] - A[1])
                nw = max(4, int(span / (0.068 * S)))
                for (v0, pr) in ((0.10, 0.006), (0.28, 0.011),
                                 (0.48, 0.016), (0.68, 0.022),
                                 (0.90, 0.028)):
                    for iw in range(nw):
                        w = (iw + 0.5) / nw
                        vmax = 1.0 - 0.15 * math.sin(math.pi * w)
                        px, pz = panel_pt(A, B, w, v0 * vmax)
                        dx = px - K[0]
                        dz = pz - K[1]
                        dl = math.hypot(dx, dz) or 1.0
                        ang = math.atan2(dx / dl, -dz / dl) \
                            + rj.uniform(-0.05, 0.05)
                        # sized from the panel's FULL depth at this line, not
                        # from the root's own radius - radius-scaled cards
                        # shrank to dust near the knuckle and the membrane
                        # showed bare with a fringe at the rim
                        ex_, ez_ = panel_pt(A, B, w, vmax)
                        D = math.hypot(ex_ - K[0], ez_ - K[1])
                        L = D * (0.24 if v0 > 0.85 else 0.32) \
                            * rj.uniform(0.94, 1.08)
                        wid = span / nw * 1.9
                        # the card is FLAT but the canopy is CAMBERED: a card
                        # held at its root's height dives under the rising
                        # swell and the membrane swallows it whole - which is
                        # why two renders showed bare pink with a rim fringe.
                        # Each card rides at the camber's peak over its own
                        # reach, so no part of it is ever below the surface.
                        vend = min(1.0, v0 + L / max(D, 1e-6))
                        if v0 <= 0.5 <= vend:
                            mb = 0.05 * S
                        else:
                            mb = max(bulge(v0), bulge(vend))
                        feather(px, pz, ang, L, wid,
                                mb + pr + 0.004 * (iw % 2),
                                "feather" if (iw + int(v0 * 10)) % 5
                                else "feather_in",
                                sag=0.05)

            # THE ARM COVERTS: two rows over the shoulder-to-knuckle edge
            for (v0, n2) in ((0.30, 7), (0.72, 8)):
                for i in range(n2):
                    t = (i + 0.5) / n2
                    ax = K[0] * t
                    az = K[1] * math.sin(t * math.pi / 2) - 0.04 * S * v0
                    L = S * 0.16 * rj.uniform(0.9, 1.1)
                    feather(ax, az, rj.uniform(-0.25, 0.25) - 0.35 * t, L,
                            L * 0.5, 0.045 + 0.005 * (i % 2), "feather",
                            sag=0.03)
            if li == 0:
                mxg, myg, mzg = xf(K[0], 0.09, K[1] + 0.02)
                GEMS.append([round(mxg, 4), round(mzg, 4),
                             round(-myg - 0.04, 4), KINDS[gi % 5]])
                gi += 1

            # THE THUMB SPIKE at the knuckle, pointing up and out
            feather(K[0], K[1] + 0.01, 0.55, S * 0.17, S * 0.05, 0.05,
                    "feather", sag=0.0)

    # the clasp the wings root into
    slot(lathe([(0.0, -0.16), (0.085, -0.13), (0.115, -0.02), (0.105, 0.10),
                (0.065, 0.20), (0.0, 0.24)], segments=20, name="clasp"),
         "gold")
    GEMS.append([0.0, 0.075, -0.10, "diamond"])

    return {"lights": [{"x": 0, "y": 0.95, "z": 0, "c": "#ffb6d4", "p": 1.1,
                        "r": 7.0}],
            "motes": {"n": 52, "r": 1.55, "h": 1.90, "y": 0.20},
            "gems": GEMS,
            "gemScale": 1.0,
            "flap": {"amp": 0.16, "rate": 0.30, "span": 2.6},
            "up": 0.30}


# ============================================================ THE WAND
def build_wand():
    """A staff rather than a wand: a length of dark wood that has kept the
    shape it grew in, with blossom breaking out of it here and there."""
    L = 1.62
    STEPS = 46
    rings = []
    for i in range(STEPS + 1):
        t = i / STEPS
        z = t * L
        # it does not grow straight, and it does not taper evenly
        # IT GREW. A staff cut from a living branch keeps the branch's own
        # lean and its own wander; at a third of this it read as a dowel with
        # flowers glued to it.
        bx = math.sin(t * 2.05 + 0.4) * 0.085 + math.sin(t * 5.9) * 0.020
        by = math.cos(t * 1.55) * 0.058 + math.sin(t * 7.3 + 1.1) * 0.016
        r = 0.0215 * (1.0 - 0.34 * t) + 0.004 * math.sin(t * 9.0)
        # a swelling at each old branch scar
        for kn in (0.22, 0.47, 0.71, 0.88):
            r += 0.0075 * math.exp(-((t - kn) / 0.035) ** 2)
        ring = []
        for k in range(12):
            th = k * math.pi * 2 / 12
            rr = r * (1.0 + 0.10 * math.sin(th * 3 + t * 6.0))
            ring.append((bx + math.cos(th) * rr, by + math.sin(th) * rr, z))
        rings.append(ring)
    slot(loft(rings, name="staff"), "wood")

    def at(t):
        z = t * L
        return (math.sin(t * 2.05 + 0.4) * 0.085 + math.sin(t * 5.9) * 0.020,
                math.cos(t * 1.55) * 0.058 + math.sin(t * 7.3 + 1.1) * 0.016,
                z, 0.0215 * (1.0 - 0.34 * t))

    GEMS = []
    KINDS = ("rose", "sapphire", "diamond", "ruby", "amethyst")
    gi = 0

    # THE BLOSSOM, WHERE IT WOULD ACTUALLY BE.
    # Five even rings of flowers at five even heights is a lamp-post with
    # decorations wired to it. Blossom breaks out where the wood was hurt -
    # at the old branch scars - and it comes out in CLUSTERS, at whatever
    # angle the light was, with the near ones open and the far ones still in
    # bud. Every spray here starts at a scar, wanders a little up or down it,
    # and leans out on its own spur; nothing sits at a round number.
    SCARS = (0.215, 0.470, 0.615, 0.720, 0.885)
    for (si, tk) in enumerate(SCARS):
        # a scar throws out between two and six, and how many is not tidy
        n = (4, 3, 2, 5, 6)[si]
        # the whole spray leans one way, the way a branch does
        lean = random.uniform(0, 6.283)
        for sfl in range(n):
            # scatter round the scar rather than dividing the circle by n
            th = lean + random.gauss(0.0, 0.95) + sfl * 1.7
            tt = tk + random.uniform(-0.035, 0.045)
            bxx, byy, bz, br = at(tt)
            out = random.uniform(0.045, 0.155)
            up = random.uniform(-0.02, 0.13)
            # the spur it grows on: it curves as it goes, and no flower is
            # ever off the staff
            SN = 6
            spr = []
            for k in range(SN + 1):
                u2 = k / SN
                # bends upward toward the light as it leaves the wood
                curve = up * (u2 ** 1.6)
                cx = bxx + math.cos(th) * (br * 0.55 + out * u2)
                cy = byy + math.sin(th) * (br * 0.55 + out * u2)
                cz = bz + curve
                rr = 0.0060 * (1.0 - 0.55 * u2) + 0.0018
                ring = []
                for q in range(6):
                    pq = q * math.pi * 2 / 6
                    ring.append((cx + math.cos(pq) * rr,
                                 cy + math.sin(pq) * rr,
                                 cz + math.sin(pq) * rr * 0.3))
                spr.append(ring)
            slot(loft(spr, name="spur"), "wood")

            px = bxx + math.cos(th) * (br * 0.55 + out)
            py = byy + math.sin(th) * (br * 0.55 + out)
            pz = bz + up

            # OPEN, HALF OPEN, OR STILL A BUD. A tree in blossom is all three
            # at once and that is most of what makes it read as alive.
            state = random.random()
            openness = 1.0 if state > 0.42 else (0.55 if state > 0.18 else 0.0)
            tilt = random.uniform(0.75, 1.35)
            face = random.uniform(0, 6.283)

            if openness > 0.0:
                npet = 5
                for pi in range(npet):
                    pa = face + pi * math.pi * 2 / npet + random.uniform(-0.16, 0.16)
                    sz2 = random.uniform(0.88, 1.15) * (0.6 + 0.4 * openness)
                    pl = lathe([(0.0, 0.0), (0.010, 0.002), (0.017, 0.007),
                                (0.019, 0.014), (0.011, 0.019), (0.0, 0.020)],
                               segments=8, name="petal")
                    pl.scale = (sz2, sz2 * 1.75, sz2 * 0.5)
                    pl.rotation_euler = (tilt * openness, 0, pa)
                    pl.location = (px + math.cos(pa) * 0.017 * openness,
                                   py + math.sin(pa) * 0.017 * openness,
                                   pz + (1.0 - openness) * 0.008)
                    bpy.context.view_layer.objects.active = pl
                    pl.select_set(True)
                    bpy.ops.object.transform_apply(location=True, rotation=True,
                                                   scale=True)
                    pl.select_set(False)
                    slot(pl, "petal")
                slot(sphere(0.0042, (px, py, pz + 0.006), seg=8, ring=6),
                     "glow_gem")
            else:
                # a bud: the petals still wrapped round each other
                bd = lathe([(0.0, 0.0), (0.008, 0.004), (0.011, 0.014),
                            (0.008, 0.026), (0.0, 0.031)], segments=8,
                           name="bud")
                bd.location = (px, py, pz)
                bpy.context.view_layer.objects.active = bd
                bd.select_set(True)
                bpy.ops.object.transform_apply(location=True)
                bd.select_set(False)
                slot(bd, "petal")

    # ------------------------------------------------------------- the head
    # EVERY FITTING GOES WHERE THE STAFF ACTUALLY IS. The staff bends, and a
    # ring built at x = 0 does not have the wood through the middle of it -
    # which is exactly what he saw. Nothing here is placed at a coordinate;
    # it is placed at whatever at() says the wood is doing at that height, and
    # every ring is made wider than the wood is thick at that point.
    def put_at(ob, t):
        bxx, byy, bz, _ = at(t)
        ob.location = (bxx, byy, 0.0)
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.transform_apply(location=True)
        ob.select_set(False)
        return ob

    def ring_at(t, extra, minor, gems=3):
        """a band round the staff, wider than the wood, with stones set in it"""
        bxx, byy, bz, br = at(t)
        rmaj = br + extra
        put_at(slot(torus(rmaj, minor, (0, 0, bz), seg=22, minor=9), "gold"), t)
        for g in range(gems):
            ga = g * math.pi * 2 / gems + t * 3.1
            GEMS.append([round(bxx + math.cos(ga) * rmaj, 4),
                         round(bz, 4),
                         round(-(byy + math.sin(ga) * rmaj), 4),
                         KINDS[(g + int(t * 7)) % 3]])

    # two bands down the shaft and one under the head
    ring_at(0.335, 0.010, 0.0062, 3)
    ring_at(0.660, 0.009, 0.0058, 3)
    ring_at(0.955, 0.011, 0.0068, 4)

    # the head proper: a swelling of grain, a socket, and the stone in it
    put_at(slot(lathe([(0.0, L - 0.010), (0.021, L + 0.002), (0.030, L + 0.020),
                       (0.026, L + 0.042), (0.017, L + 0.056), (0.0, L + 0.060)],
                      segments=18, name="head"), "wood"), 1.0)
    # THE SOCKET the pommel sits in - a cup with a lip, so the stone is HELD
    # and not balanced on the end of a stick
    put_at(slot(lathe([(0.0, L + 0.052), (0.026, L + 0.056), (0.034, L + 0.072),
                       (0.038, L + 0.092), (0.030, L + 0.098),
                       (0.021, L + 0.090), (0.019, L + 0.070),
                       (0.0, L + 0.064)], segments=20, name="socket"),
                "gold"), 1.0)
    # the claws that hold it
    bxx0, byy0, _, _ = at(1.0)
    for c in range(4):
        ca = c * math.pi / 2 + 0.4
        cl = box(0.010, 0.014, 0.046,
                 (bxx0 + math.cos(ca) * 0.033, byy0 + math.sin(ca) * 0.033,
                  L + 0.096), (0.30 * math.sin(ca), -0.30 * math.cos(ca), ca))
        slot(cl, "gold")
    # THE POMMEL
    put_at(slot(lathe([(0.0, L + 0.086), (0.024, L + 0.098), (0.032, L + 0.118),
                       (0.026, L + 0.140), (0.014, L + 0.152),
                       (0.0, L + 0.156)], segments=20, name="pommel"),
                "glow_core"), 1.0)
    GEMS.append([round(bxx0, 4), round(L + 0.120, 4), round(-byy0, 4), "diamond"])
    for c in range(3):
        ca = c * math.pi * 2 / 3 + 0.9
        GEMS.append([round(bxx0 + math.cos(ca) * 0.030, 4),
                     round(L + 0.118, 4),
                     round(-(byy0 + math.sin(ca) * 0.030), 4),
                     KINDS[c % 3]])

    # a gold ferrule at the foot, so it does not end in raw end-grain
    put_at(slot(lathe([(0.0, 0.0), (0.027, 0.0), (0.029, 0.020),
                       (0.025, 0.050), (0.0245, 0.052)], segments=16,
                      name="ferrule"), "gold"), 0.0)

    return {"lights": [{"x": 0, "y": 1.10, "z": 0, "c": "#ff6fb2", "p": 1.1,
                        "r": 5.5}],
            "motes": {"n": 30, "r": 0.20, "h": 1.55, "y": 0.30},
            "gems": GEMS,
            "gemScale": 0.30,
            "up": 0.0}


# ======================================================== THE ASTROLABE
def build_astrolabe():
    """The one relic that is knowledge rather than power.

    An astrolabe is a flat brass disc - the MATER - hollowed into a well that
    holds a stack of engraved plates, one per latitude. Over them turns the
    RETE: a pierced openwork map of the sky, cut away to almost nothing so
    that the plate can be read through it, with a pointer for every named star
    and a broad off-centre ring for the ecliptic. Over that a straight RULE,
    and through the whole stack a pin with a horse-headed wedge through it -
    which is why the pin is called the horse.

    Everything on it turns. That is the whole point of the instrument and it
    is what the engine is given: the rete, the rule and the alidade on the
    back are separate slots so they can be driven, and the star-pointers are
    written out as gem anchors so each one can be lit as a star.

    Hung by its throne, as it is used: the ring at the top is what you hold it
    by, and the instrument hangs plumb from it."""

    GEMS = []
    R = 0.30                       # the mater's radius - a big, courtly one
    T0 = 0.030                     # how thick the body is

    # ------------------------------------------------------------ the mater
    # a disc with a raised rim, hollowed into a well
    slot(lathe([(0.0, -T0 * 0.5), (R * 0.94, -T0 * 0.5), (R, -T0 * 0.34),
                (R, T0 * 0.5), (R * 0.90, T0 * 0.5), (R * 0.90, -T0 * 0.16),
                (0.0, -T0 * 0.16)], segments=64, name="mater"), "gold")

    # THE LIMB: the outer rim is graduated, and a graduation you cannot count
    # is a decoration. Three hundred and sixty is too many to read at this
    # size and too many to build; it is marked every five degrees, with a
    # longer mark at every thirty, which is how it is actually engraved.
    for d in range(72):
        a = d * math.pi * 2 / 72
        lng = (d % 6 == 0)
        h = 0.030 if lng else 0.016
        w = 0.0075 if lng else 0.0040
        b = box(w, h, 0.006,
                (math.cos(a) * (R - h * 0.5 - 0.004),
                 math.sin(a) * (R - h * 0.5 - 0.004), T0 * 0.5 + 0.001),
                (0, 0, a + math.pi / 2))
        slot(b, "steel")

    # ------------------------------------------- the plate, under the rete
    # the three circles every plate carries: Cancer, the equator, Capricorn,
    # and the horizon cutting across them
    slot(lathe([(0.0, -T0 * 0.14), (R * 0.88, -T0 * 0.14), (R * 0.88, -T0 * 0.10),
                (0.0, -T0 * 0.10)], segments=48, name="plate"), "steel")
    for rr in (R * 0.30, R * 0.55, R * 0.84):
        slot(torus(rr, 0.0022, (0, 0, -T0 * 0.09), seg=56, minor=6), "gold")
    # the almucantars: the arcs of equal altitude, crowded near the zenith
    for k in range(7):
        u = (k + 1) / 8.0
        rr = R * 0.80 * (1.0 - u * 0.86)
        oy = R * 0.30 * u
        slot(torus(rr, 0.0016, (0, oy, -T0 * 0.075), seg=44, minor=5), "steel")

    # ------------------------------------------------------------- the rete
    # THE PIERCED SKY. It is cut away to almost nothing, because you have to
    # read the plate through it.
    RETE = []

    def rete_part(ob):
        RETE.append(ob)
        return slot(ob, "rete")

    rete_part(torus(R * 0.86, 0.0060, (0, 0, T0 * 0.28), seg=64, minor=8))
    # the ecliptic: a broad band set off-centre, which is the thing that makes
    # an astrolabe an astrolabe
    ECC = R * 0.24
    rete_part(torus(R * 0.58, 0.0075, (0, ECC, T0 * 0.28), seg=56, minor=8))
    rete_part(torus(R * 0.50, 0.0045, (0, ECC, T0 * 0.28), seg=56, minor=6))
    # the bar across the middle and the strut down it
    rete_part(box(R * 1.70, 0.011, 0.010, (0, 0, T0 * 0.28)))
    rete_part(box(0.011, R * 1.70, 0.010, (0, 0, T0 * 0.28)))

    # THE STAR POINTERS. Each is a curved spike reaching in off the ecliptic
    # or the outer ring to a point, and the point IS the star - so that is
    # where the stone goes.
    STARS = 14
    for k in range(STARS):
        a = k * math.pi * 2 / STARS + 0.22
        # alternate between the outer ring and the ecliptic band
        if k % 2 == 0:
            bx0, by0, rr0 = 0.0, 0.0, R * 0.86
        else:
            bx0, by0, rr0 = 0.0, ECC, R * 0.54
        sx0 = bx0 + math.cos(a) * rr0
        sy0 = by0 + math.sin(a) * rr0
        # it points inward and to one side, the way a real pointer is cut
        ln = R * (0.18 + 0.14 * ((k * 7) % 5) / 4.0)
        aa = a + math.pi + 0.42 * (1 if k % 2 else -1)
        tipx = sx0 + math.cos(aa) * ln
        tipy = sy0 + math.sin(aa) * ln
        SN = 5
        spike = []
        for q in range(SN + 1):
            u = q / SN
            cx = sx0 + (tipx - sx0) * u
            cy = sy0 + (tipy - sy0) * u
            # it curves as it goes
            cx += -math.sin(aa) * 0.030 * math.sin(u * math.pi)
            cy += math.cos(aa) * 0.030 * math.sin(u * math.pi)
            rw = 0.0080 * (1.0 - u) + 0.0011
            ring = []
            for q2 in range(6):
                pq = q2 * math.pi * 2 / 6
                ring.append((cx + math.cos(pq) * rw,
                             cy + math.sin(pq) * rw,
                             T0 * 0.28 + math.sin(pq) * 0.0045))
            spike.append(ring)
        rete_part(loft(spike, name="pointer"))
        GEMS.append([round(tipx, 4), round(T0 * 0.30, 4), round(-tipy, 4),
                     ("sapphire", "ruby", "diamond")[k % 3]])

    # ------------------------------------------------------------- the rule
    RULE = []
    rl = box(R * 1.80, 0.016, 0.007, (0, 0, T0 * 0.42))
    RULE.append(rl)
    slot(rl, "rule")
    for sgn in (-1, 1):
        e = box(0.030, 0.026, 0.007, (sgn * R * 0.86, 0, T0 * 0.42))
        RULE.append(e)
        slot(e, "rule")

    # ---------------------------------------------------- the pin and horse
    slot(cyl(0.011, 0.011, T0 * 1.5, (0, 0, T0 * 0.2), verts=14), "steel")
    slot(lathe([(0.0, T0 * 0.48), (0.020, T0 * 0.52), (0.024, T0 * 0.62),
                (0.016, T0 * 0.70), (0.0, T0 * 0.72)], segments=16,
               name="horsehead"), "gold")
    GEMS.append([0.0, round(T0 * 0.66, 4), 0.0, "diamond"])

    # ------------------------------------------------------------ the throne
    # the shaped bracket at the top and the ring it hangs from
    slot(box(0.085, 0.055, 0.020, (0, R + 0.020, 0)), "gold")
    slot(lathe([(0.0, 0.0), (0.030, 0.006), (0.038, 0.024), (0.030, 0.040),
                (0.0, 0.046)], segments=18, name="knop"), "gold")
    kn = parts[-1]
    kn.rotation_euler = (math.pi / 2, 0, 0)
    kn.location = (0, R + 0.048, 0)
    bpy.context.view_layer.objects.active = kn
    kn.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    kn.select_set(False)
    rg = torus(0.042, 0.010, (0, R + 0.105, 0), seg=26, minor=9,
               rot=(math.pi / 2, 0, 0))
    slot(rg, "gold")
    GEMS.append([0.0, 0.0, -(R + 0.105), "sapphire"])

    # The anchors above were written in the flat frame, in the same
    # (x, height, -y) convention the exporter uses. The instrument is then
    # turned a quarter upright, so they are turned with it - or fourteen
    # stars stay lying on the floor where the disc used to be.
    TURNED = [[g[0], -g[2], g[1], g[3]] for g in GEMS]

    return {"lights": [{"x": 0, "y": 0.0, "z": 0.10, "c": "#ffb45e", "p": 0.75,
                        "r": 3.2}],
            "motes": {"n": 26, "r": 0.42, "h": 0.60, "y": -0.28},
            "gems": TURNED,
            "gemScale": 0.34,
            "turns": {"rete": 0.055, "rule": -0.13},
            "up": 0.62}


# =========================================================== THE AVATAR
def build_avatar():
    """The player, aniconic - his order: 'only a dress with a beautiful
    crown... no body will be inside it, and the crown will hover above it.'

    Named from the theme so it cannot drift:
      - a full-length gown in the rose damask of the palace cloth, EMPTY -
        the collar opens onto nothing, the sleeves hang hollow;
      - the folds are UNEQUAL gores, deep at the hem and gone at the bodice,
        seeded so the mirror test fails (the organic law);
      - a gold sash at the waist with falling tails, gold four-point stars
        embroidered down the skirt (the approved star shape, never a cut
        solid);
      - the crown HOVERS above the open collar: a thin gold circlet with
        alternating points, every point tipped by a twinkling star gem, one
        bright star floating in its centre;
      - baby pink dominant, the glow left to the engine's bloom.
    """
    GEMS = []
    KINDS = ("rose", "diamond", "sapphire", "ruby", "amethyst")
    rj = random.Random(4207)
    H = 1.45                      # the collar height; the crown floats above

    # THE GOWN: one loft, hem to collar. The cross-section carries the
    # gores: a sum of unequal sine folds whose depth dies toward the bodice.
    # AN ABAYA FALLS, IT DOES NOT BALLOON. The first gown bellied out like a
    # tea-cosy and he named it: "too round... looks almost like granny."
    # This one drops nearly straight from the shoulder, and the fullness is
    # LAYERS, not width: a white underdress to the floor, the pale pink
    # jacquard over it ending higher, and a short over-tier from the chest -
    # three hems, the way a layered abaya actually reads.
    NF = [(5, 0.040, rj.uniform(0, 6.3)), (8, 0.027, rj.uniform(0, 6.3)),
          (11, 0.016, rj.uniform(0, 6.3)), (3, 0.022, rj.uniform(0, 6.3))]

    def gown_layer(zlo, zhi, r_of, seedoff, slname, th=0.011):
        rows = []
        NZ = 10
        for iz in range(NZ + 1):
            z = zlo + (zhi - zlo) * iz / NZ
            t = min(1.0, z / H)
            r = r_of(z)
            depth = max(0.0, 1.0 - t) ** 1.6
            ring = []
            for k in range(30):
                a = k / 30.0 * 2 * math.pi
                f = 1.0
                for (nk, amp, ph) in NF:
                    f += amp * depth * math.sin(nk * a + ph + seedoff)
                cy = -0.055 * (1.0 - t) ** 2
                ring.append((math.cos(a) * r * f,
                             cy + math.sin(a) * r * f
                             * (1.05 if math.sin(a) < 0 else 1.0), z))
            rows.append(ring)
        ob = loft(rows, close=True, cap_a=True, cap_b=False,
                  name="g" + slname + str(int(zlo * 10)))
        so_ = ob.modifiers.new("s", 'SOLIDIFY')
        so_.thickness = th
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=so_.name)
        slot(ob, slname)

    def rbase(z):
        """the abaya line: straight fall, a soft shoulder, a narrow collar"""
        # clamp: a float hair past 1.0 makes (negative)**1.35 COMPLEX and
        # kills the whole build
        t = min(1.0, z / H)
        body = 0.155 + 0.245 * max(0.0, 1.0 - t) ** 1.35
        if t <= 0.84:
            return body
        u = min(1.0, (t - 0.84) / 0.15)
        u = u * u * (3 - 2 * u)
        return body * (1.0 - u) + 0.072 * u

    gown_layer(0.00, H, lambda z: rbase(z) - 0.016, 0.0, "feather")  # white under
    gown_layer(0.14, H, lambda z: rbase(z) + 0.006, 1.7, "cloth")    # the jacquard
    gown_layer(0.58, 1.30, lambda z: rbase(z) + 0.019, 3.9, "cloth") # the over-tier

    # THE SLEEVES: hollow tubes arcing out and down from the shoulders,
    # nothing inside them, cuffs open and flared
    for sd in (1, -1):
        pts = [(0.130, 1.335, 0.042), (0.190, 1.285, 0.044),
               (0.238, 1.170, 0.047), (0.268, 1.020, 0.050),
               (0.284, 0.840, 0.058), (0.292, 0.660, 0.072),
               (0.296, 0.560, 0.088)]
        srows = []
        for (px, pz, pr) in pts:
            ring = []
            for k in range(10):
                a = k / 10.0 * 2 * math.pi
                ring.append((sd * (px + math.cos(a) * pr * 0.75),
                             math.sin(a) * pr,
                             pz + math.cos(a) * pr * 0.28))
            srows.append(ring)
        sl = loft(srows, close=True, cap_a=True, cap_b=False,
                  name="slv%d" % (sd > 0))
        so2 = sl.modifiers.new("s", 'SOLIDIFY')
        so2.thickness = 0.010
        bpy.context.view_layer.objects.active = sl
        bpy.ops.object.modifier_apply(modifier=so2.name)
        slot(sl, "cloth")

    # THE COLLAR: a slim gold band round the empty neck
    slot(torus(0.082, 0.012, (0, 0, H), seg=20, minor=8), "gold")

    def star4(x, y, z, s, tilt):
        """the approved star shape: two long thin bipyramids crossed - the
        points STRETCHED, the waist a sliver, never a squarish solid"""
        ct, st = math.cos(tilt), math.sin(tilt)
        for horiz in (False, True):
            rows2 = []
            for (e, w) in ((-1.0, 0.03), (0.0, 1.0), (1.0, 0.03)):
                ring = []
                for q in (0.0, 1.57, 3.14, 4.71):
                    ww = s * 0.14 * w
                    if horiz:
                        lx, ly, lz = e * s, math.sin(q) * ww, math.cos(q) * ww
                    else:
                        lx, ly, lz = math.cos(q) * ww, math.sin(q) * ww, e * s
                    ring.append((x + lx * ct - ly * st,
                                 y + lx * st + ly * ct, z + lz))
                rows2.append(ring)
            slot(loft(rows2, close=True, cap_a=False, cap_b=False,
                      name="st"), "gold")

    # JEWELRY HANGS - his correction: no strict round belt. A necklace of
    # three draped chains falls from the collar down the chest, each carrying
    # a star pendant; a loose chain rides the hips, lower at one side, with
    # droplets hanging from it. Chains are thin lofted tubes in a catenary.
    def chain(pts, r=0.0065):
        rows3 = []
        for (px, py, pz) in pts:
            rows3.append([(px + math.cos(q) * r, py + math.sin(q) * r * 0.7,
                           pz + math.sin(q) * r)
                          for q in (0.0, 1.05, 2.09, 3.14, 4.19, 5.24)])
        slot(loft(rows3, close=True, cap_a=True, cap_b=True, name="ch"),
             "gold")

    for (drop, wide) in ((0.14, 0.052), (0.22, 0.060), (0.31, 0.066)):
        pts = []
        for i in range(9):
            u = i / 8.0 - 0.5
            px = u * 2 * wide
            sag2 = drop * (1.0 - (2 * u) ** 2)
            pts.append((px, -0.185 - 0.5 * sag2, H - 0.045 - sag2))
        chain(pts)
        GEMS.append([0.0, round(H - 0.045 - drop - 0.028, 4),
                     round(0.185 + 0.5 * drop, 4), KINDS[int(drop * 100) % 5]])
        star4(0.0, -0.185 - 0.5 * drop, H - 0.045 - drop - 0.02, 0.020, 0.0)

    # the hip chain: a full loop, swung low at the front-left
    hpts = []
    for i in range(25):
        a = i / 24.0 * 2 * math.pi
        low = 0.11 * max(0.0, math.cos(a - 2.4)) ** 2
        rr = rbase(0.88) + 0.030
        hpts.append((math.cos(a) * rr, math.sin(a) * rr, 0.88 - low))
    chain(hpts, r=0.0075)
    for ad in (2.4, 1.6, 3.1):
        rr = rbase(0.88) + 0.030
        hx2, hy2 = math.cos(ad) * rr, math.sin(ad) * rr
        hz2 = 0.88 - 0.11 * max(0.0, math.cos(0.0)) ** 2 - 0.055
        chain([(hx2, hy2, 0.86), (hx2 * 1.01, hy2 * 1.01, hz2)], r=0.004)
        star4(hx2 * 1.02, hy2 * 1.02, hz2 - 0.02, 0.017, ad)
        GEMS.append([round(hx2 * 1.04, 4), round(hz2 - 0.045, 4),
                     round(-hy2 * 1.04, 4), KINDS[int(ad * 10) % 5]])

    # gold stars embroidered down the skirt, unevenly, as the relics wear
    for i in range(9):
        a = rj.uniform(0, 6.283)
        t = rj.uniform(0.08, 0.55)
        z = H * t
        rr = 0.50 - 0.32 * t
        star4(math.cos(a) * rr * 1.01, math.sin(a) * rr * 1.01, z,
              rj.uniform(0.030, 0.048), a)
        # (no gem sprites on the skirt: at portrait distance one mid-twinkle
        # flare read as a headlight through the cloth - the gold stars carry
        # the skirt; the sprites live at the collar and the crown)

    # THE CROWN, HOVERING: nothing holds it, which is the point
    CZ = H + 0.17
    slot(torus(0.096, 0.015, (0, 0, CZ), seg=24, minor=8), "gold")
    slot(torus(0.090, 0.009, (0, 0, CZ + 0.032), seg=24, minor=6), "gold")
    # four broad points, and a small gold orb between each pair - a crown,
    # not a fence of nails
    NPT = 8
    for k in range(NPT):
        a = k / float(NPT) * 2 * math.pi
        px, py = math.cos(a) * 0.096, math.sin(a) * 0.096
        if k % 2 == 0:
            tall = 0.108
            prows = []
            for (hh, ww) in ((0.0, 0.030), (0.35, 0.022), (0.72, 0.013),
                             (1.0, 0.003)):
                prows.append([(px + math.cos(q + a) * ww,
                               py + math.sin(q + a) * ww,
                               CZ + 0.012 + tall * hh)
                              for q in (0.0, 1.57, 3.14, 4.71)])
            slot(loft(prows, close=True, cap_a=True, cap_b=True,
                      name="pt"), "gold")
            GEMS.append([round(px, 4), round(CZ + 0.012 + tall + 0.02, 4),
                         round(-py, 4), KINDS[(k // 2) % 5]])
        else:
            slot(sphere(0.020, (px, py, CZ + 0.052), seg=10, ring=8), "gold")
    # the one bright star floating inside the circlet
    GEMS.append([0.0, round(CZ + 0.085, 4), 0.0, "diamond"])
    # and a pair riding the collar
    GEMS.append([0.078, round(H + 0.01, 4), 0.0, "rose"])
    GEMS.append([-0.078, round(H + 0.01, 4), 0.0, "rose"])

    return {"lights": [{"x": 0, "y": 1.15, "z": 0, "c": "#ffb6d4", "p": 0.9,
                        "r": 5.5},
                       # warm light AT the crown, so the gold reads as gold
                       {"x": 0, "y": 1.80, "z": 0.35, "c": "#ffd9a0",
                        "p": 1.3, "r": 3.2}],
            "motes": {"n": 34, "r": 0.85, "h": 2.05, "y": 0.10},
            "gems": GEMS,
            "gemScale": 0.65,
            # a zero-amplitude beat: the cloth never bends, but the beat's
            # clock drives the SHED - her gems fall, as ordered
            "flap": {"amp": 0.0, "rate": 0.22, "span": 2.0},
            "up": 0.0}


BUILDERS = {"sabre": build_sabre, "carpet": build_carpet,
            "wings": build_wings, "wand": build_wand,
            "astrolabe": build_astrolabe, "avatar": build_avatar}

if KIND not in BUILDERS:
    raise SystemExit("no such relic: %s (have %s)"
                     % (KIND, ", ".join(sorted(BUILDERS))))
META = BUILDERS[KIND]()

# ------------------------------------------------------------- assemble
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND

# AN ASTROLABE HANGS. It is built flat, in the plane it is drawn in, because
# every circle and every pointer on it is easier to place that way - and then
# it is stood upright, which is how the instrument is actually used: held up
# by the ring of its throne, hanging plumb, and sighted along.
# Blender is Z-up and the file is Y-up, so a disc left in the XY plane arrives
# lying on the floor. Turned a quarter about X here, its face comes to the
# viewer and its throne comes to the top.
if KIND == "astrolabe":
    ob.rotation_euler = (math.pi / 2, 0, 0)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.transform_apply(rotation=True)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0004)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.cube_project(cube_size=0.55)
bpy.ops.object.mode_set(mode='OBJECT')

# A CARPET'S DESIGN IS LAID ON IT FROM ABOVE. A cube projection cuts a flat
# thing into six pieces and lays a sixth of the picture on each, which for a
# rug means the border appears in the middle of the field. Everything on it is
# projected straight down instead, scaled so the whole design covers the whole
# carpet exactly once.
if KIND == "carpet":
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    xs = [p2.x for p2 in bb]
    ys = [p2.y for p2 in bb]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    uvl = ob.data.uv_layers.active.data
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            vi = ob.data.loops[li].vertex_index
            co = ob.data.vertices[vi].co
            uvl[li].uv = ((co.x - x0) / max(x1 - x0, 1e-6),
                          (co.y - y0) / max(y1 - y0, 1e-6))

m = ob.modifiers.new("bv", 'BEVEL')
m.width = 0.0022
m.segments = 2
m.limit_method = 'ANGLE'
m.angle_limit = math.radians(38)
bpy.ops.object.modifier_apply(modifier=m.name)

bpy.ops.object.shade_smooth()
try:
    ob.data.use_auto_smooth = True
    ob.data.auto_smooth_angle = math.radians(34)
except AttributeError:
    try:
        bpy.ops.object.modifier_add(type='SMOOTH_BY_ANGLE')
        ob.modifiers[-1]["Input_1"] = math.radians(34)
        bpy.ops.object.modifier_apply(modifier=ob.modifiers[-1].name)
    except Exception as e:
        print("auto-smooth unavailable:", e)

# --------------------------------------------------- what each slot is made of
# Base colour only. The engine turns every glow_* slot into an emissive
# material at load, because that is where the bloom and the light live.
# BABY PINK IS THE HOUSE COLOUR. Not a tint on top of something else - it
# is what these things are MADE of, and every other colour here is chosen to
# sit under it: the metals go rose, the wood goes warm rather than cold, the
# feathers go from white to the palest pink, and the deep colours are only
# there to give the pink an edge to be pink against. A set of objects that
# share one dominant colour reads as a set; five objects each with their own
# idea of what they are reads as a shelf.
SLOT_LOOK = {
    # rose-tinted watered steel: pale, warm, and never grey
    "steel":     (0.94, 0.76, 0.82),
    # rose gold rather than yellow gold, or the fittings fight the pink
    "gold":      (0.92, 0.62, 0.58),
    "wood":      (0.30, 0.17, 0.15),
    "grip":      (0.68, 0.30, 0.45),
    "cloth":     (0.90, 0.62, 0.76),
    # THE PALEST PINK, not white. At 0.95 white the vanes were as bright as
    # the stones set in them and the wing came out as one sheet with nothing
    # readable on it; and a white feather beside a rose-gold clasp and a pink
    # shaft looks like a feather from somewhere else.
    "feather":   (0.96, 0.84, 0.88),
    "feather_in": (0.95, 0.55, 0.72),
    # BLOSSOM IS PINK. At almost white the petals had nothing left to be
    # bloomed with, so every flower on the carpet's border and on the staff
    # came out as a white blob and the shape of the petals went with it.
    "petal":     (0.93, 0.52, 0.68),
    # the rete is the pierced sky and the rule is the straight edge over it -
    # brass, but each a shade off the mater so the three read apart as they
    # turn across one another
    "rete":      (0.94, 0.68, 0.62),
    "rule":      (0.90, 0.74, 0.78),
    "glow_core": (1.00, 0.62, 0.80),
    "glow_edge": (1.00, 0.72, 0.86),
    "glow_gem":  (1.00, 0.84, 0.92),
}
# some slots wear a photograph rather than a colour. Which one depends on
# the relic: 'cloth' is a rug on the carpet and would be something else on
# anything else, so it is keyed by both.
SLOT_TEX = {
    ("carpet", "cloth"): "t_rug_d.jpg",
    ("wand", "wood"): "t_woodp_d.jpg",
    # the avatar's gown wears the jacquard dyed nearly white - baby pink
    # living in the weave's shadows
    ("avatar", "cloth"): "t_avatar_d.jpg",
}

for name in SLOTS:
    sm = bpy.data.materials["mat_" + name]
    sm.use_nodes = True
    nt2 = sm.node_tree
    b = nt2.nodes["Principled BSDF"]
    c = SLOT_LOOK.get(name, (0.6, 0.6, 0.6))
    b.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1)
    METALS = ("steel", "gold", "rete", "rule")
    b.inputs["Roughness"].default_value = 0.26 if name in METALS else 0.8
    if name in METALS:
        b.inputs["Metallic"].default_value = 0.9
    tf = SLOT_TEX.get((KIND, name))
    if tf:
        tp = os.path.abspath(os.path.join(ASSETS, tf))
        if os.path.exists(tp):
            img2 = bpy.data.images.load(tp)
            tn3 = nt2.nodes.new('ShaderNodeTexImage')
            tn3.image = img2
            nt2.links.new(tn3.outputs['Color'], b.inputs['Base Color'])
            img2.pack()

me = ob.data
me.calc_loop_triangles()
print("RESULT %s verts=%d tris=%d slots=%d"
      % (KIND, len(me.vertices), len(me.loop_triangles), len(SLOTS)))

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB',
                          use_selection=True, export_apply=True,
                          export_yup=True)
with open(os.path.splitext(OUT)[0] + ".fx.json", "w") as f:
    json.dump(META, f)
print("WROTE", OUT)
