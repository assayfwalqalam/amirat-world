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
        # the heart of it, lit - and SMALL, because the bloom round a lit
        # centre is what took the petals off the first set
        slot(sphere(0.0028 * sc2, (bx2, by2, bz2 + 0.005 * sc2), seg=6, ring=5),
             "glow_gem")

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
    for (k2, (fx2, fy2)) in enumerate(ring_pts):
        # a little in or out of the band, and never twice the same size
        off = 0.020 if (k2 % 2 == 0) else -0.020
        nx2 = 1.0 if abs(fx2) > abs(fy2) else 0.0
        fx3 = fx2 + off * nx2 * (1 if fx2 > 0 else -1)
        fy3 = fy2 + off * (1 - nx2) * (1 if fy2 > 0 else -1)
        blossom(fx3, fy3, 0.033,
                random.uniform(0.86, 1.20),
                random.uniform(0, 6.283),
                random.uniform(0.10, 0.30), 0)

    # and a smaller run of them inside the guard stripe, so the field is not
    # cut off from the border by a hard line
    for k2 in range(20):
        a2 = k2 * math.pi * 2 / 20 + 0.3
        blossom(math.cos(a2) * (W * 0.315), math.sin(a2) * (D * 0.300), 0.033,
                random.uniform(0.55, 0.78), random.uniform(0, 6.283),
                random.uniform(0.08, 0.24), 0)

    # the central medallion, in relief over the one that is woven into it
    med = lathe([(0.0, 0.0), (0.07, 0.004), (0.115, 0.010), (0.140, 0.017),
                 (0.095, 0.023), (0.040, 0.026), (0.0, 0.027)], segments=20,
                name="medallion")
    med.location = (0, 0, 0.030)
    bpy.context.view_layer.objects.active = med
    med.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    med.select_set(False)
    # on the quieter glow: at full strength this one dome burned out the
    # whole centre of the carpet, medallion, field and all
    slot(med, "glow_edge")

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
    return {"lights": [{"x": 0, "y": 1.45, "z": 0, "c": "#e07fd8", "p": 0.85,
                        "r": 5.2}],
            "motes": {"n": 46, "r": 1.05, "h": 0.85, "y": 0.06, "flat": 1},
            "up": 0.0}


# =========================================================== THE WINGS
def build_wings():
    """SEVEN WINGS ON EACH SIDE, spread.

    A wing is a LEADING EDGE with feathers hanging behind it. The edge runs
    from the shoulder out and up; every feather roots on that edge and sweeps
    BACKWARD, more so the further out you go, so they lie almost parallel and
    overlap like tiles. Fourteen of those, fanned from one shoulder at seven
    different pitches, is a seraph rather than a bird - and at this size the
    fan is most of what you see, so no two wings get the same length or the
    same curve.

    THE GEMS ARE NOT IN THE MESH. They are written out as anchor points and
    the engine makes them: one instanced mesh for all of them, which is what
    lets each one twinkle on its own clock, follow the wings as they beat, and
    be shed as a slow fall of light when they do. A gem baked into the model
    can do none of that.

    A feather's width lies in Z and its thickness in Y, because the sweep is a
    rotation about Y - anything laid out in Y would stay edge-on to the viewer
    however wide it was made."""

    GEMS = []           # (x, y, z, kind) - handed to the engine
    KINDS = ("sapphire", "ruby", "diamond")

    # Each wing: how far it reaches, how high it sets off, its pitch in the
    # fan, and how many feathers it carries. The middle pair are the longest,
    # which is what makes a fan read as wings and not as a wheel.
    WINGS = [
        # span, lift,  pitch, feathers, row2
        (1.55, 0.10, -0.62, 11, 7),
        (2.05, 0.22, -0.30, 13, 9),
        (2.42, 0.38,  0.02, 14, 9),
        (2.55, 0.58,  0.34, 14, 9),
        (2.30, 0.80,  0.66, 13, 8),
        (1.86, 0.98,  0.96, 11, 7),
        (1.38, 1.10,  1.24, 9, 5),
    ]

    def vane(length, width, lead, thick):
        """one feather lying along +X, width in Z, thin in Y"""
        rings = []
        N = 7
        for i in range(N + 1):
            t = i / N
            w = width * math.sin(min(1.0, t * 1.06) ** 0.78 * math.pi) ** 0.62
            if t < 0.07:
                w *= t / 0.07
            th = thick * (1.0 - 0.55 * t) + 0.0010
            x = t * length
            bow = -0.075 * t * t * length / 0.6
            wl, wt = w * lead, w * (1.0 - lead)
            rings.append([
                (x, 0.0, bow + wt),
                (x, +th, bow + wt * 0.42),
                (x, +th, bow - wl * 0.42),
                (x, 0.0, bow - wl),
                (x, -th, bow - wl * 0.42),
                (x, -th, bow + wt * 0.42),
            ])
        return rings

    def place(ob, px, pz, ang, side, py=0.0):
        ob.rotation_euler = (0, ang, 0)
        ob.location = (side * px, py, pz)
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True)
        ob.select_set(False)
        return ob

    gi = 0
    for side in (-1, 1):
        for (wi, (span, lift, pitch, nf, nf2)) in enumerate(WINGS):

            def edge_at(u):
                """a point on this wing's leading edge. The edge is an arc,
                not a line: it leaves the shoulder steeply and flattens as it
                reaches, which is the curve every long wing has."""
                r = 0.16 + span * u
                a = pitch + 0.52 * math.sin(u * 1.25)
                return (math.cos(a) * r, lift + math.sin(a) * r)

            for (row, n, lmul, wmul, back) in ((0, nf, 1.00, 1.00, 0.0),
                                               (1, nf2, 0.55, 0.84, 0.085)):
                for i in range(n):
                    t = i / max(n - 1.0, 1.0)
                    ex, ez = edge_at(t)
                    ex -= back * 0.95
                    ez += back * 0.62
                    # nearly straight down at the shoulder, nearly straight
                    # out at the tip
                    ang = pitch + 1.24 - t * 1.10
                    ln = (0.34 + 0.62 * t ** 0.85) * lmul * (0.72 + span * 0.24)
                    wd = (0.175 - 0.030 * t) * wmul * (0.80 + span * 0.10)

                    fo = loft(vane(ln, wd, 0.38, 0.0068), name="vane")
                    place(fo, ex, ez, ang, side)
                    slot(fo, "feather")

                    go = loft(vane(ln * 0.93, wd * 0.42, 0.38, 0.0076),
                              name="inner")
                    place(go, ex, ez, ang, side, 0.0)
                    slot(go, "feather_in")

                    qo = loft(vane(ln * 0.88, wd * 0.070, 0.5, 0.0084),
                              name="shaft")
                    place(qo, ex, ez, ang, side, 0.0)
                    slot(qo, "glow_edge")

                    # THE STONES SET IN THE WHITE. Two per feather on the
                    # outer row, one on the inner, out along the vane where
                    # the white actually is.
                    for (gt, gs) in ((0.42, 0.30), (0.68, -0.26)):
                        if row == 1 and gt > 0.5:
                            continue
                        gx = ex + math.cos(ang) * ln * gt
                        gz = ez - math.sin(ang) * ln * gt
                        # off the shaft, into the vane
                        gx += -math.sin(ang) * wd * gs
                        gz += -math.cos(ang) * wd * gs
                        # WRITTEN IN THE FRAME THE FILE IS EXPORTED IN.
                        # Blender is Z-up and the glTF is Y-up, so an anchor
                        # stored as (x, thickness, height) here arrives in the
                        # engine as (x, height, thickness) - which put four
                        # hundred and fifty stones in a flat grid on the floor
                        # under the wings instead of in the feathers.
                        GEMS.append([round(side * gx, 4), round(gz, 4),
                                     -0.010, KINDS[gi % 3]])
                        gi += 1

            # the arm the feathers are set into
            arm = []
            for i in range(13):
                t = i / 12.0
                ex, ez = edge_at(t)
                r = 0.040 * (1.0 - 0.62 * t) + 0.008
                ring = []
                for k in range(9):
                    th = k * math.pi * 2 / 9
                    ring.append((side * (ex + math.cos(th) * r * 0.55),
                                 math.sin(th) * r,
                                 ez + math.cos(th) * r * 0.9))
                arm.append(ring)
            slot(loft(arm, name="arm"), "feather")

    # the fourteen wings meet at a clasp rather than in mid air
    slot(lathe([(0.0, -0.16), (0.075, -0.135), (0.105, -0.03), (0.098, 0.08),
                (0.062, 0.155), (0.0, 0.185)], segments=20, name="clasp"),
         "gold")
    GEMS.append([0.0, 0.075, -0.052, "diamond"])

    return {"lights": [{"x": 0, "y": 0.95, "z": 0, "c": "#ff7ec0", "p": 1.0,
                        "r": 6.5}],
            "motes": {"n": 44, "r": 1.30, "h": 1.70, "y": 0.20},
            "gems": GEMS,
            "flap": {"span": 2.6, "amp": 0.30, "rate": 0.42},
            "up": 0.34}


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
    KINDS = ("sapphire", "ruby", "diamond")
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


BUILDERS = {"sabre": build_sabre, "carpet": build_carpet,
            "wings": build_wings, "wand": build_wand}

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
SLOT_LOOK = {
    # A LITTLE PINK IN EVERYTHING, not a lot. Watered steel already goes warm
    # grey; this leans it rose so the blade belongs to the light coming out of
    # its own fuller instead of sitting cold beside it.
    "steel":     (0.80, 0.70, 0.76),
    "gold":      (0.80, 0.56, 0.30),
    "wood":      (0.22, 0.14, 0.09),
    "grip":      (0.38, 0.12, 0.24),
    "cloth":     (0.42, 0.16, 0.34),
    # A LITTLE OFF WHITE. At 0.95 the vanes were as bright as the stones set
    # in them and the wing came out as one white sheet with nothing readable
    # on it; feathers are not paper anyway.
    "feather":   (0.80, 0.79, 0.83),
    "feather_in": (0.92, 0.44, 0.66),
    # BLOSSOM IS PINK. At almost white the petals had nothing left to be
    # bloomed with, so every flower on the carpet's border and on the staff
    # came out as a white blob and the shape of the petals went with it.
    "petal":     (0.92, 0.30, 0.55),
    "glow_core": (1.00, 0.36, 0.70),
    "glow_edge": (1.00, 0.50, 0.80),
    "glow_gem":  (1.00, 0.72, 0.92),
}
# some slots wear a photograph rather than a colour. Which one depends on
# the relic: 'cloth' is a rug on the carpet and would be something else on
# anything else, so it is keyed by both.
SLOT_TEX = {
    ("carpet", "cloth"): "t_rug_d.jpg",
    ("wand", "wood"): "t_woodp_d.jpg",
}

for name in SLOTS:
    sm = bpy.data.materials["mat_" + name]
    sm.use_nodes = True
    nt2 = sm.node_tree
    b = nt2.nodes["Principled BSDF"]
    c = SLOT_LOOK.get(name, (0.6, 0.6, 0.6))
    b.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1)
    b.inputs["Roughness"].default_value = 0.22 if name in ("steel", "gold") else 0.8
    if name in ("steel", "gold"):
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
