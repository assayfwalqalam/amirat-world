# Trees v3, to the Bannerlord bar (shots/ref/bannerlord_1..4): thick proper
# trunks, real radiating bough structure, and canopies built from dense
# CLUSTERS of leaf cards so they read as volumes with depth, never one flat
# sheet. Every tree at least two storeys. Many variants per kind.
#   blender --background --python make_tree.py -- <kind> <seed> <out.glb> [assets]
# Kinds: olive, plane, cypress, tamarisk, fig, giant, pine
import bpy, json, math, os, random, sys
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KIND = argv[0] if argv else "olive"
SEED = int(argv[1]) if len(argv) > 1 else 1
OUT = argv[2] if len(argv) > 2 else (KIND + ".glb")
ASSETS = argv[3] if len(argv) > 3 else "assets"
# SIZE TIER. His order: some twice the size of the biggest tree, some three
# times, some four or more, and the bigger it is the heavier its trunk and
# logs. Height takes the scale straight; the wood takes it to the power of
# 1.12, because a tree four times as tall is more than four times as stout.
SCALE = float(argv[4]) if len(argv) > 4 else 1.0
RSCALE = SCALE ** 1.12
# Leaves do NOT grow with the tree. Scaled straight, an eighty metre tree gets
# eight metre leaf sheets; instead the cards stay near leaf size and there are
# far more of them.
CARDK = SCALE ** -0.55
NK = SCALE ** 1.15
random.seed(SEED * 4967 + sum(ord(c) for c in KIND) * 61)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8

COLLIDERS = []
wood, leaf = [], []


def rec(loc, hx, hy, hz):
    COLLIDERS.append({"c": [round(loc[0], 2), round(loc[2], 2), round(-loc[1], 2)],
                      "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


WOOD_V, WOOD_F, WOOD_UV = [], [], []


def limb(p0, direction, length, r0, r1, segs=None, crook=0.3, min_dz=None,
         gnarl=0.0, arc=0.0, flare=1.0, sides=None):
    """One limb, built as ONE CONTINUOUS TUBE with an irregular section.

    It used to be a stack of twelve-sided cones with end caps. That gives a
    trunk flat facets down its silhouette, a hard ring at every joint where
    one cone meets the next, and a perfectly circular section the whole way
    up: machined, not grown. Here there are no joints at all, the section is
    LOBED, the lobes travel and change along the length, and the foot spreads
    into root fingers rather than a cone skirt.

    gnarl  the wood swells, pinches and throws hard elbows
    arc    the limb rises and then falls away
    flare  the foot spreads where it meets the ground
    """
    r0 *= RSCALE
    r1 *= RSCALE
    segs = segs or max(3, int(length / 0.9))
    # A thick limb given four rings changes radius in visible steps and grows a
    # collar. Ring spacing follows the limb's own girth.
    segs = max(segs, int(length / max(0.55, 1.15 * (r0 + r1))))
    segs = min(segs, 26)
    if sides is None:
        # facets must follow the ACTUAL radius. A four metre trunk at sixteen
        # sides has twenty-two degree chords, which read as flat plates however
        # smoothly it is shaded -- and these trunks are now metres thick.
        sides = int(max(5, min(30, 7 + r0 * 5.0)))
    dx, dy, dz = direction
    nn = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    d = Vector((dx / nn, dy / nn, dz / nn))
    p = Vector((p0[0], p0[1], p0[2]))
    # SOCKET the limb into its parent. Each limb is its own tube, so starting
    # it exactly at the parent's tip leaves the parent's open rim standing
    # proud as a hard ledge round the trunk. Backing the first ring inside the
    # parent's wood buries the joint.
    p = p - d * (r0 * 1.15)
    seglen = length / segs
    gph = [random.uniform(0, 6.283) for _ in range(4)]

    # walk the path
    ring_c = [p.copy()]
    ring_t = [d.copy()]
    for i in range(segs):
        w = crook * seglen
        d = Vector((d.x + random.uniform(-w, w) * 0.15,
                    d.y + random.uniform(-w, w) * 0.15,
                    d.z + random.uniform(-w * 0.5, w) * 0.15))
        if gnarl > 0.0 and random.random() < 0.22 * gnarl:
            ea = random.uniform(0, 6.283)
            kick = 0.55 * gnarl
            d = Vector((d.x + math.cos(ea) * kick, d.y + math.sin(ea) * kick,
                        d.z + random.uniform(-0.35, 0.22) * gnarl))
        if arc:
            d = Vector((d.x, d.y, d.z - arc / float(segs)))
        if min_dz is not None and d.z < min_dz:
            d = Vector((d.x, d.y, min_dz))
        if d.length < 1e-6:
            d = Vector((0, 0, 1))
        d.normalize()
        p = p + d * seglen
        ring_c.append(p.copy())
        ring_t.append(d.copy())

    # the radius of every ring, swelling and pinching along the run
    radii = []
    for i in range(segs + 1):
        t = i / float(segs)
        r = r0 + (r1 - r0) * t
        if gnarl > 0.0:
            r *= (1.0 + gnarl * (0.13 * math.sin(i * 1.05 + gph[0])
                                 + 0.07 * math.sin(i * 2.30 + gph[1])))
        radii.append(max(0.012, r))

    # carry a frame along the path so the bark does not spin round it
    nrm = Vector((0.0, 0.0, 1.0)).cross(ring_t[0])
    if nrm.length < 1e-4:
        nrm = Vector((1.0, 0.0, 0.0)).cross(ring_t[0])
    nrm.normalize()
    base_i = len(WOOD_V)
    cols = sides + 1
    vlen = 0.0
    uoff = random.uniform(0.0, 8.0)
    # ONE circumference for the whole limb. Taking it per ring means the same
    # column of vertices lands at a different U wherever the limb is thinner,
    # so the bark shears between one ring and the next and the trunk wears a
    # herringbone. The wood stretches a little where it tapers instead, which
    # is what bark actually does.
    circ = 6.283 * max(r0, r1, 0.02)
    for i in range(segs + 1):
        if i > 0:
            q = ring_t[i - 1].rotation_difference(ring_t[i])
            nrm = (q @ nrm).normalized()
            vlen += seglen
        bino = ring_t[i].cross(nrm).normalized()
        r = radii[i]
        t = i / float(segs)
        for j in range(cols):
            a = 6.283 * j / sides
            lob = 1.0
            if gnarl > 0.0:
                # gentle: enough that the section is never a circle, not so
                # much that consecutive facets fold into a star
                lob += gnarl * (0.075 * math.sin(3 * a + gph[0] + i * 0.35)
                                + 0.050 * math.sin(5 * a + gph[1] - i * 0.22)
                                + 0.030 * math.sin(7 * a + gph[2] + i * 0.60))
            if flare > 1.0:
                # ROOT FINGERS: the spread is not a cone, it is three or four
                # buttresses, and only at the very foot
                fz = max(0.0, 1.0 - t * 5.0)
                lob += (flare - 1.0) * fz * fz * (0.10 + 0.40 *
                        max(0.0, math.sin(3 * a + gph[3])) ** 2.2)
            rr = r * lob
            v = ring_c[i] + (nrm * math.cos(a) + bino * math.sin(a)) * rr
            WOOD_V.append((v.x, v.y, v.z))
            WOOD_UV.append(((j / float(sides)) * circ / BARKSCALE + uoff,
                            vlen / BARKSCALE))
    for i in range(segs):
        for j in range(sides):
            a0 = base_i + i * cols + j
            b0 = base_i + (i + 1) * cols + j
            WOOD_F.append((a0, a0 + 1, b0 + 1, b0))
    return (p.x, p.y, p.z), (d.x, d.y, d.z)


LEAF_V, LEAF_F = [], []


def card(at, size):
    """One leaf card, tilted freely.

    Written straight into one shared vertex list. Adding five thousand cards
    as five thousand Blender objects, each through an operator call, took
    minutes per tree; as raw geometry it takes no time at all, and a canopy
    is worth thousands of cards."""
    m = Euler((random.uniform(0.6, 2.5),
               random.uniform(0, 6.283),
               random.uniform(0, 6.283)), 'XYZ').to_matrix()
    h = size * 0.5
    i0 = len(LEAF_V)
    for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h)):
        v = m @ Vector((dx, dy, 0.0))
        LEAF_V.append((at[0] + v.x, at[1] + v.y, at[2] + v.z))
    LEAF_F.append((i0, i0 + 1, i0 + 2, i0 + 3))


def cluster(at, r, n=None):
    """A DENSE cluster of cards round one point: the unit of foliage. Cards
    overlap heavily so the mass reads solid from every side, never a sheet."""
    # A crown you can see the sky through is a scatter of paper sprigs on bare
    # sticks. Real foliage is a MASS: cards packed until the middle is opaque
    # and light only breaks through at the edges. Cards are two triangles, so
    # density is nearly free -- there was no reason to be sparing.
    n = int((n or random.randint(20, 28)) * NK)
    for _ in range(n):
        a = random.uniform(0, 6.283)
        el = random.uniform(-0.6, 1.1)
        rr = random.uniform(0, r * 0.62)
        cx = at[0] + math.cos(a) * math.cos(el) * rr
        cy = at[1] + math.sin(a) * math.cos(el) * rr
        cz = at[2] + math.sin(el) * rr * 0.8
        card((cx, cy, cz), random.uniform(r * 0.95, r * 1.55) * CARDK)


def spray(p0, p1, r, n=None, taper=0.55):
    """Foliage laid ALONG a branch, from p0 to p1, thinning toward the tip.

    A cluster is a sphere, and a tree built of spheres reads as a bunch of
    pom-poms hung on sticks however many you use. Real foliage follows the
    wood: it runs out along the branch and thins as the branch thins."""
    n = n or 16
    for i in range(n):
        t = random.uniform(0.0, 1.0)
        # along the branch, with a little scatter round it
        bx = p0[0] + (p1[0] - p0[0]) * t
        by = p0[1] + (p1[1] - p0[1]) * t
        bz = p0[2] + (p1[2] - p0[2]) * t
        rr = r * (1.0 - taper * t)
        a = random.uniform(0, 6.283)
        el = random.uniform(-0.5, 1.0)
        cx = bx + math.cos(a) * math.cos(el) * rr * random.uniform(0, 0.9)
        cy = by + math.sin(a) * math.cos(el) * rr * random.uniform(0, 0.9)
        cz = bz + math.sin(el) * rr * random.uniform(0, 0.7)
        card((cx, cy, cz), random.uniform(rr * 1.05, rr * 1.75))


def crown_of_clusters(at, spread, k, cr, squash=0.92):
    k = int(k * NK)
    """k clusters strewn through an ellipsoid: canopy WITH internal depth.
    Squashed hard it reads as a mushroom umbrella on a stick; a real crown is
    nearly as deep as it is wide, and it hangs BELOW its own centre too."""
    for _ in range(k):
        a = random.uniform(0, 6.283)
        el = random.uniform(-0.85, 1.05)
        rr = random.uniform(spread * 0.12, spread)
        cx = at[0] + math.cos(a) * math.cos(el) * rr
        cy = at[1] + math.sin(a) * math.cos(el) * rr
        cz = at[2] + math.sin(el) * rr * squash
        cluster((cx, cy, cz), cr)


# The variants used to differ only by which numbers the seed happened to draw,
# so five olives were five of the same olive. A variant now takes a HABIT: how
# it grew. Short-trunked and spreading, tall and upright, leaning off the wind,
# many-stemmed from the root, or forked low into two leaders.
HABITS = ["upright", "spreading", "leaning", "multistem", "forked"]
HABIT = HABITS[(SEED - 1) % len(HABITS)]
HB = {
    "upright":   dict(trunk=1.20, branch=0.85, elev=1.35, spread=0.80, squash=1.10, lean=0.04, stems=1),
    "spreading": dict(trunk=0.68, branch=1.35, elev=0.50, spread=1.35, squash=0.76, lean=0.10, stems=1),
    "leaning":   dict(trunk=1.00, branch=1.00, elev=0.88, spread=1.02, squash=0.94, lean=0.44, stems=1),
    "multistem": dict(trunk=0.52, branch=1.15, elev=1.05, spread=1.18, squash=0.96, lean=0.20, stems=3),
    "forked":    dict(trunk=0.80, branch=0.72, elev=1.12, spread=1.06, squash=1.00, lean=0.14, stems=2),
}[HABIT]

# cut from photographs (tools/make_blossom_from_photo.py), never drawn
BLOSSOM_SHEETS = ["blossom_pink_1.png", "blossom_pink_2.png", "blossom_pink_3.png",
                  "blossom_white_2.png", "blossom_pale_2.png", "blossom_violet_2.png",
                  "blossom_violet_1.png", "blossom_white_1.png"]
BLOSSOM = BLOSSOM_SHEETS[(SEED - 1) % len(BLOSSOM_SHEETS)]

GREEN = {
    "olive": (0.80, 0.86, 0.66), "plane": (0.82, 1.0, 0.72),
    "cypress": (0.38, 0.52, 0.40), "tamarisk": (0.84, 0.95, 0.70),
    "fig": (0.70, 0.95, 0.62), "giant": (0.78, 0.98, 0.70),
    "pine": (0.45, 0.62, 0.45),
    # the bloom carries its own colour in the sheet, so it is barely tinted
    "blossom": (0.98, 0.95, 0.95),
}[KIND]
LEAFTEX = {
    "olive": "leafcard_fine.png", "tamarisk": "leafcard_fine.png",
    "cypress": "leafcard_fine.png", "plane": "leafcard_broad.png",
    "fig": "leafcard_broad2.png", "giant": "leafcard_broad.png",
    "pine": "leafcard_fine.png",
    "blossom": BLOSSOM,
}[KIND]
# The trunks had NO texture at all: their colour came from a vertex-colour
# node, which is why they read as smooth blurred tubes. Real photographed
# bark now, CC0 from Poly Haven, with the furrow scale set per kind.
# 512, not 2k: this image is PACKED INTO every tree glb, so a 2k sheet costs
# 1.7MB per variant and fifty megabytes across the set (tools/shrink_bark.py)
_BARKTEX, _BARKSCALE = {
    "olive":    ("t_bark512_d.jpg", 0.75),
    "plane":    ("t_bark512_d.jpg", 1.10),
    "fig":      ("t_bark512_d.jpg", 0.95),
    "tamarisk": ("t_bark512_d.jpg", 0.65),
    "cypress":  ("t_barkpine512_d.jpg", 0.70),
    "pine":     ("t_barkpine512_d.jpg", 1.00),
    "giant":    ("t_barkold512_d.jpg", 1.70),
    "blossom":  ("t_barkold512_d.jpg", 1.90),
}[KIND]
# Bark on a giant is bigger bark: deeper, wider furrows. Held at the small-tree
# scale, a five metre trunk wraps sixteen copies of the sheet round itself and
# reads as corduroy.
BARKTEX = _BARKTEX
BARKSCALE = _BARKSCALE * (RSCALE ** 0.62)

# every tree is at least two storeys; trunks are logs
if KIND == "olive":
    H = random.uniform(6.5, 8.5) * SCALE
    tip, d = limb((0, 0, 0), (HB["lean"] + random.uniform(-0.1, 0.1),
                              random.uniform(-0.1, 0.1), 1),
                  H * 0.4 * HB["trunk"], 0.42, 0.24, crook=0.45, min_dz=0.66)
    for _ in range(max(3, int(random.randint(4, 6) * HB["branch"]))):
        a = random.uniform(0, 6.283)
        t2, d2 = limb(tip, (math.cos(a), math.sin(a),
                            random.uniform(0.6, 1.2) * HB["elev"]),
                      H * 0.42, 0.16, 0.05, crook=0.5)
        cluster(t2, H * 0.16)
        t3, _ = limb(t2, (math.cos(a + 0.7), math.sin(a + 0.7), random.uniform(0.3, 0.8)),
                     H * 0.18, 0.05, 0.02, segs=2, crook=0.5)
        cluster(t3, H * 0.13)
    crown_of_clusters((tip[0], tip[1], tip[2] + H * 0.16),
                      H * 0.32 * HB["spread"], 26, H * 0.15, HB["squash"])
    rec((0, 0, H * 0.3), 0.5, 0.5, H * 0.3)

elif KIND == "plane":
    H = random.uniform(11.0, 15.0) * SCALE
    tip, d = limb((0, 0, 0), (HB["lean"] * 0.7, 0, 1),
                  H * 0.4 * HB["trunk"], 0.55, 0.3, crook=0.22, min_dz=0.78)
    for _ in range(max(4, int(random.randint(5, 7) * HB["branch"]))):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 0.85, math.sin(a) * 0.85, 1.05 * HB["elev"]),
                     H * 0.4, 0.2, 0.06, crook=0.35)
        cluster(t2, H * 0.15)
        t3, _ = limb(t2, (math.cos(a + 0.8), math.sin(a + 0.8), random.uniform(0.5, 1.0)),
                     H * 0.16, 0.06, 0.025, segs=2, crook=0.45)
        cluster(t3, H * 0.12)
    crown_of_clusters((tip[0], tip[1], tip[2] + H * 0.2),
                      H * 0.34 * HB["spread"], 30, H * 0.14, HB["squash"])
    rec((0, 0, H * 0.28), 0.6, 0.6, H * 0.28)

elif KIND == "cypress":
    H = random.uniform(8.5, 12.0) * SCALE
    limb((0, 0, 0), (0, 0, 1), H * 0.24, 0.3, 0.16, crook=0.1, min_dz=0.9)
    n = int(H * 4.5)
    for i in range(n):
        t = i / float(n)
        rr = (1.0 - 0.75 * t) * (1.0 + random.uniform(-0.12, 0.12))
        z = H * 0.1 + t * H * 0.9
        a = random.uniform(0, 6.283)
        cluster((math.cos(a) * rr * 0.4, math.sin(a) * rr * 0.4, z),
                (0.6 + rr * 0.55), n=4)
    rec((0, 0, H * 0.4), 0.5, 0.5, H * 0.4)

elif KIND == "tamarisk":
    H = random.uniform(6.0, 8.0) * SCALE
    for _ in range(max(2, int(random.randint(3, 4) * HB["branch"]))):
        a = random.uniform(0, 6.283)
        tip, _ = limb((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0),
                      (math.cos(a) * 0.45, math.sin(a) * 0.45, 1.25),
                      H * 0.62, 0.2, 0.05, crook=0.4)
        cluster(tip, H * 0.17)
        t3, _ = limb(tip, (math.cos(a + 1.1), math.sin(a + 1.1), 0.7),
                     H * 0.2, 0.05, 0.02, segs=2, crook=0.5)
        cluster(t3, H * 0.13)
    crown_of_clusters((0, 0, H * 0.72), H * 0.32 * HB["spread"], 22, H * 0.15, HB["squash"])
    rec((0, 0, H * 0.3), 0.45, 0.45, H * 0.3)

elif KIND == "fig":
    H = random.uniform(6.5, 9.0) * SCALE
    tip, d = limb((0, 0, 0), (HB["lean"], 0, 1),
                  H * 0.3 * HB["trunk"], 0.5, 0.3, crook=0.35, min_dz=0.7)
    for _ in range(max(4, int(random.randint(5, 7) * HB["branch"]))):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 1.25, math.sin(a) * 1.25,
                            random.uniform(0.3, 0.7) * HB["elev"]),
                     H * 0.55 * HB["spread"], 0.18, 0.055, crook=0.45)
        cluster(t2, H * 0.18)
        cluster(((tip[0] + t2[0]) / 2, (tip[1] + t2[1]) / 2, (tip[2] + t2[2]) / 2 + H * 0.06),
                H * 0.14)
    rec((0, 0, H * 0.25), 0.55, 0.55, H * 0.25)

elif KIND == "pine":
    # the Bannerlord forest wall: straight trunk, whorls of boughs
    # shortening toward the top, dense dark foliage
    H = random.uniform(10.0, 15.0) * SCALE
    limb((0, 0, 0), (0, 0, 1), H, 0.42, 0.06, segs=7, crook=0.06, min_dz=0.95)
    whorls = random.randint(6, 8)
    for wla in range(whorls):
        t = 0.3 + 0.68 * wla / (whorls - 1)
        z = H * t
        blen = H * 0.24 * (1.15 - t)
        for b in range(random.randint(4, 6)):
            a = random.uniform(0, 6.283)
            t2, _ = limb((0, 0, z), (math.cos(a), math.sin(a), random.uniform(0.05, 0.28)),
                         blen, 0.09 * (1.2 - t), 0.02, segs=2, crook=0.25)
            cluster(t2, blen * 0.5, n=5)
            cluster((t2[0] * 0.6, t2[1] * 0.6, z + blen * 0.1), blen * 0.42, n=4)
    cluster((0, 0, H * 1.0), H * 0.06, n=5)
    rec((0, 0, H * 0.4), 0.5, 0.5, H * 0.4)

elif KIND == "blossom":
    # To his photographs: a short thick FLARED trunk splitting low into three
    # or four heavy leaders, every one gnarled and elbowed, and the boughs
    # reaching UP and OUT -- never hanging down, never ending in a ball. The
    # bloom runs ALONG the wood and thins toward the tips, so the dark
    # architecture reads right through it.
    H = random.uniform(19.0, 24.0) * SCALE
    L = HB["lean"]
    nlead = 3 if HB["stems"] < 3 else 4
    base, _ = limb((0, 0, 0), (L * 0.5, 0, 1), H * 0.20 * HB["trunk"],
                   1.55, 1.15, segs=4, crook=0.30, min_dz=0.70,
                   gnarl=0.85, flare=1.55)
    for li_ in range(nlead):
        la = li_ * (6.283 / nlead) + random.uniform(-0.35, 0.35)
        lead, _ = limb(base, (math.cos(la) * 0.55 + L, math.sin(la) * 0.55, 1.15),
                       H * 0.32, 0.92, 0.44, segs=5, crook=0.40,
                       min_dz=0.42, gnarl=0.95)
        spray(base, lead, 1.5, n=10, taper=0.25)
        for bi_ in range(max(4, int(random.randint(5, 7) * HB["branch"]))):
            a = la + random.uniform(-1.25, 1.25)
            # up and out: the rise never goes negative
            rise = random.uniform(0.55, 1.35) * HB["elev"]
            bough, _ = limb(lead, (math.cos(a) * 1.05, math.sin(a) * 1.05, rise),
                            H * 0.34 * HB["spread"], 0.36, 0.10,
                            segs=5, crook=0.38, gnarl=0.72, min_dz=0.02)
            spray(lead, bough, 1.9, n=26, taper=0.30)
            for tw in range(2):
                ta = a + random.uniform(-1.1, 1.1)
                twig, _ = limb(bough, (math.cos(ta), math.sin(ta),
                                       random.uniform(0.25, 0.95)),
                               H * 0.15, 0.08, 0.03, segs=3, crook=0.5,
                               gnarl=0.45, min_dz=0.0)
                spray(bough, twig, 1.7, n=16, taper=0.42)
    rec((0, 0, H * 0.16), 1.5, 1.5, H * 0.16)

else:                        # giant: the bustan patriarch, 5-7 storeys
    H = random.uniform(16.0, 21.0) * SCALE
    tip, d = limb((0, 0, 0), (HB["lean"] * 0.6, 0, 1), H * 0.36 * HB["trunk"], 1.25, 0.66,
                  segs=6, crook=0.18, min_dz=0.82)
    for _ in range(max(5, int(random.randint(6, 8) * HB["branch"]))):
        a = random.uniform(0, 6.283)
        t2, _ = limb(tip, (math.cos(a) * 0.9, math.sin(a) * 0.9, random.uniform(0.55, 1.0)),
                     H * 0.4, 0.36, 0.1, crook=0.35)
        cluster(t2, H * 0.11)
        t3, _ = limb(t2, (math.cos(a + 0.9), math.sin(a + 0.9), random.uniform(0.4, 0.9)),
                     H * 0.16, 0.09, 0.03, segs=2, crook=0.4)
        cluster(t3, H * 0.09)
    crown_of_clusters((tip[0], tip[1], tip[2] + H * 0.22),
                      H * 0.32 * HB["spread"], 34, H * 0.10, HB["squash"])
    for _ in range(5):
        a = random.uniform(0, 6.283)
        limb((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.5),
             (math.cos(a), math.sin(a), -0.5), 1.8, 0.34, 0.07, segs=3, crook=0.3)
    rec((0, 0, H * 0.22), 1.2, 1.2, H * 0.22)


# ------------------------------------------------------------- assemble
def join_and_colour(objs, name, tint, jitter_amt):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    me = ob.data
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    for poly in me.polygons:
        g = 1.0 + random.uniform(-jitter_amt, jitter_amt)
        for li in poly.loop_indices:
            col.data[li].color = (min(1.0, tint[0] * g), min(1.0, tint[1] * g),
                                  min(1.0, tint[2] * g), 1.0)
    bpy.ops.object.shade_smooth()
    return ob


def join_leaf_cards(objs, tint):
    me = bpy.data.meshes.new("leafmesh")
    me.from_pydata(LEAF_V, [], LEAF_F)
    me.update()
    ob = bpy.data.objects.new("leaf", me)
    bpy.context.collection.objects.link(ob)
    uv0 = me.uv_layers.new(name="UVMap")
    corner = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    for poly in me.polygons:
        for j, li in enumerate(poly.loop_indices):
            uv0.data[li].uv = corner[j % 4]
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    for poly in me.polygons:
        g = 1.0 + random.uniform(-0.24, 0.24)
        for li in poly.loop_indices:
            col.data[li].color = (min(1.0, tint[0] * g), min(1.0, tint[1] * g),
                                  min(1.0, tint[2] * g), 1.0)
    m = bpy.data.materials.new("leafcards")
    m.use_nodes = True
    m.blend_method = 'CLIP'
    m.alpha_threshold = 0.32
    m.use_backface_culling = False
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.9
    path = os.path.abspath(os.path.join(ASSETS, "src", LEAFTEX))
    img = bpy.data.images.load(path)
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    vcn = nt.nodes.new('ShaderNodeVertexColor')
    vcn.layer_name = "ao"
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 1.0
    nt.links.new(tn.outputs['Color'], mix.inputs['Color1'])
    nt.links.new(vcn.outputs['Color'], mix.inputs['Color2'])
    nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(tn.outputs['Alpha'], b.inputs['Alpha'])
    img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


# The vertex colour used to BE the trunk colour, so it was near black. It is
# now only a per-face shade jitter riding on top of the bark photo, which
# means it must sit near white -- and never above 1.0, because glTF clamps a
# vertex-colour lift and the wood goes pastel.
def build_wood(tint, jitter_amt):
    """One mesh for all the wood, from the tube geometry."""
    me = bpy.data.meshes.new("woodmesh")
    me.from_pydata(WOOD_V, [], WOOD_F)
    me.update()
    ob = bpy.data.objects.new("wood", me)
    bpy.context.collection.objects.link(ob)
    uv0 = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv0.data[li].uv = WOOD_UV[me.loops[li].vertex_index]
    while len(me.color_attributes):
        me.color_attributes.remove(me.color_attributes[0])
    col = me.color_attributes.new(name="ao", type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = col
    for poly in me.polygons:
        g = 1.0 + random.uniform(-jitter_amt, jitter_amt)
        for li in poly.loop_indices:
            col.data[li].color = (min(1.0, tint[0] * g), min(1.0, tint[1] * g),
                                  min(1.0, tint[2] * g), 1.0)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    return ob


w_ob = build_wood((0.74, 0.68, 0.61), 0.10)
l_ob = join_leaf_cards(leaf, GREEN)

# the wood keeps its own bark material; the join then carries both slots
mat = bpy.data.materials.new("bark")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.92
bpath = os.path.abspath(os.path.join(ASSETS, BARKTEX))
bimg = bpy.data.images.load(bpath)
btn = nt.nodes.new('ShaderNodeTexImage')
btn.image = bimg
vc = nt.nodes.new('ShaderNodeVertexColor')
vc.layer_name = "ao"
bmix = nt.nodes.new('ShaderNodeMixRGB')
bmix.blend_type = 'MULTIPLY'
bmix.inputs['Fac'].default_value = 1.0
nt.links.new(btn.outputs['Color'], bmix.inputs['Color1'])
nt.links.new(vc.outputs['Color'], bmix.inputs['Color2'])
nt.links.new(bmix.outputs['Color'], bsdf.inputs['Base Color'])
bimg.pack()
w_ob.data.materials.clear()
w_ob.data.materials.append(mat)

bpy.ops.object.select_all(action='DESELECT')
w_ob.select_set(True)
l_ob.select_set(True)
bpy.context.view_layer.objects.active = w_ob
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = KIND

me = ob.data
me.calc_loop_triangles()
print("RESULT %s/%d verts=%d tris=%d" % (KIND, SEED, len(me.vertices), len(me.loop_triangles)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
try:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_vertex_color='ACTIVE')
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLLIDERS}, f)
print("WROTE", OUT)
