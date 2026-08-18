# THE QASR - the fortress-palace compound, built to the owner's drawn layout
# and grown by his orders: curtain modules on all four faces, corner towers,
# six attached minarets, a riwaq court with garden and fountain; seven unique
# storeys on the great centre block; real interiors (the hall, the minaret
# stairs); sapphire domes with a faint inner glow and firefly sparkles.
#
# FAST: no bpy.ops per part. Every part appends raw vertex/face data into
# per-material arrays and the whole palace becomes nine meshes at the end.
# The op-based version took 2.5 hours; this takes under two minutes.
#
#   blender --background --python make_palace.py -- <out.glb> [assets]
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "qasr.glb"
ASSETS = argv[1] if len(argv) > 1 else "assets"
GOLDSMALL = not (len(argv) > 2 and argv[2] == "allsapph")   # his yes, 2026-08-18
random.seed(9)

bpy.ops.wm.read_factory_settings(use_empty=True)

QSCALE = 1.4
COLS = []
DOORS = []
FLIES = []


def col(cx, cy, cz, hx, hy, hz):
    COLS.append({"c": [round(cx, 2), round(cz, 2), round(-cy, 2)],
                 "h": [round(hx, 2), round(hz, 2), round(hy, 2)]})


# ---------------------------------------------------------------- the pools
# each material owns one growing pool of geometry
class Pool:
    def __init__(self, name):
        self.name = name
        self.v = []            # (x, y, z)
        self.f = []            # tuples of vert indices
        self.smooth = []       # one flag per face

    def quad(self, a, b, c, d, smooth=False):
        self.f.append((a, b, c, d))
        self.smooth.append(smooth)

    def tri(self, a, b, c, smooth=False):
        self.f.append((a, b, c))
        self.smooth.append(smooth)


stone = Pool("stone")
gold = Pool("gold")
wood = Pool("wood")
rug = Pool("rug")
glow = Pool("glow")
earth = Pool("earth")
water = Pool("water")
sapph = Pool("sapph")
spark = Pool("spark")
sparkv = Pool("sparkv")


def rot_z(pts, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return [(x * c - y * s, x * s + y * c, z) for (x, y, z) in pts]


def rot_y(pts, tilt):
    c, s = math.cos(tilt), math.sin(tilt)
    return [(x * c + z * s, y, -x * s + z * c) for (x, y, z) in pts]


def box(sx, sy, sz, loc, pool, yaw=0.0, tilt=0.0):
    """A cuboid. tilt is about local Y, applied before yaw about Z."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    pts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
           (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    if tilt:
        pts = rot_y(pts, tilt)
    if yaw:
        pts = rot_z(pts, yaw)
    b0 = len(pool.v)
    lx, ly, lz = loc
    pool.v.extend([(x + lx, y + ly, z + lz) for (x, y, z) in pts])
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
              (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        pool.quad(b0 + q[0], b0 + q[1], b0 + q[2], b0 + q[3])


def cyl(r, h, loc, pool, verts=24, r_top=None, smooth=True):
    """A cylinder (or cone frustum), capped."""
    rt = r if r_top is None else r_top
    b0 = len(pool.v)
    lx, ly, lz = loc
    for (rr, zz) in ((r, lz - h / 2), (rt, lz + h / 2)):
        for i in range(verts):
            a = i / verts * 2 * math.pi
            pool.v.append((lx + math.cos(a) * rr, ly + math.sin(a) * rr, zz))
    for i in range(verts):
        j = (i + 1) % verts
        pool.quad(b0 + i, b0 + j, b0 + verts + j, b0 + verts + i, smooth=smooth)
    cb = len(pool.v)
    pool.v.append((lx, ly, lz - h / 2))
    pool.v.append((lx, ly, lz + h / 2))
    for i in range(verts):
        j = (i + 1) % verts
        pool.tri(cb, b0 + j, b0 + i)
        pool.tri(cb + 1, b0 + verts + i, b0 + verts + j)


def sphere(r, loc, pool, seg=12, rings=8, zscale=1.0):
    b0 = len(pool.v)
    lx, ly, lz = loc
    grid = []
    for ri in range(1, rings):
        ph = ri / rings * math.pi
        row = []
        for si in range(seg):
            th = si / seg * 2 * math.pi
            row.append(len(pool.v))
            pool.v.append((lx + r * math.sin(ph) * math.cos(th),
                           ly + r * math.sin(ph) * math.sin(th),
                           lz + r * math.cos(ph) * zscale))
        grid.append(row)
    top = len(pool.v); pool.v.append((lx, ly, lz + r * zscale))
    bot = len(pool.v); pool.v.append((lx, ly, lz - r * zscale))
    for si in range(seg):
        sj = (si + 1) % seg
        pool.tri(top, grid[0][si], grid[0][sj], smooth=True)
        pool.tri(bot, grid[-1][sj], grid[-1][si], smooth=True)
    for ri in range(len(grid) - 1):
        for si in range(seg):
            sj = (si + 1) % seg
            pool.quad(grid[ri][si], grid[ri][sj], grid[ri + 1][sj], grid[ri + 1][si], smooth=True)


# -------------------------------------------------------------- the shapes
def onion_profile(n):
    ctrl = [(0.00, 0.72), (0.06, 0.88), (0.16, 1.00), (0.30, 1.02),
            (0.44, 0.94), (0.58, 0.78), (0.70, 0.58), (0.80, 0.40),
            (0.88, 0.25), (0.94, 0.13), (0.98, 0.05), (1.00, 0.0)]
    pts = []
    for i in range(n + 1):
        t = i / n
        r = ctrl[-1][1]
        for k in range(len(ctrl) - 1):
            t0, r0 = ctrl[k]; t1, r1 = ctrl[k + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0 or 1); f = f * f * (3 - 2 * f)
                r = r0 + (r1 - r0) * f
                break
        pts.append([r, 1.06 * (t ** 0.92)])
    # The control joints leave a tangent break every eighth ring or so, and
    # a glossy dome shows every one as a layer line. A narrow smoothing pass
    # cannot reach across a break that wide: a wide-window average, three
    # times over, melts them without losing the onion's belly and point.
    for _pass in range(3):
        rr = [p2[0] for p2 in pts]
        n2 = len(rr)
        for i in range(1, n2 - 1):
            lo = max(0, i - 3); hi = min(n2, i + 4)
            pts[i][0] = sum(rr[lo:hi]) / (hi - lo)
    return [(r, z) for (r, z) in pts]


SPARK_ANCHORS = []


def dome(cx, cy, base_z, belly_r, height, ribs=16, drum=True, seg=None, shell=None):
    """A smooth SAPPHIRE onion dome; the finial stays gold. shell overrides
    the dome pool (the gold-small-domes preview)."""
    sh = shell or sapph
    if drum:
        cyl(belly_r * 0.74, belly_r * 0.7, (cx, cy, base_z + belly_r * 0.35), stone, verts=28)
        z0 = base_z + belly_r * 0.7
    else:
        z0 = base_z
    nseg = seg or max(48, int(belly_r * 14))
    prof = onion_profile(max(56, int(belly_r * 10)))
    rows = []
    for (rf, zf) in prof:
        row = []
        for s in range(nseg):
            th = s / nseg * 2 * math.pi
            rr = belly_r * rf
            row.append(len(sh.v))
            sh.v.append((cx + math.cos(th) * rr, cy + math.sin(th) * rr, z0 + zf * height))
        rows.append(row)
    for i in range(len(rows) - 1):
        for s in range(nseg):
            s2 = (s + 1) % nseg
            sh.quad(rows[i][s], rows[i][s2], rows[i + 1][s2], rows[i + 1][s], smooth=True)
    tipz = z0 + prof[-1][1] * height
    tip = len(sh.v); sh.v.append((cx, cy, tipz + 0.01))
    for s in range(nseg):
        s2 = (s + 1) % nseg
        sh.tri(rows[-1][s], rows[-1][s2], tip, smooth=True)
    for i, br in enumerate((belly_r * 0.06, belly_r * 0.045, belly_r * 0.03)):
        sphere(br, (cx, cy, tipz + height * 0.05 + i * belly_r * 0.11), gold, seg=10, rings=6)
    cyl(belly_r * 0.018, height * 0.30, (cx, cy, tipz + height * 0.16), gold, verts=8)
    SPARK_ANCHORS.append((cx, cy, z0 + height * 0.55, belly_r))


def ogee(t):
    t = 2 * t - 1
    a = abs(t)
    return math.sqrt(max(0.0, 1 - a * a)) * 0.72 + (1 - a) * 0.28


def arch(cx, cy, z0, w, h, depth, pool, frame=0.55, face=(0, -1), lit=True):
    """A pointed-arch opening with an explicit outward FACING.
    lit=True amber panel · False stone panel · None OPEN (no panel)."""
    fl = math.hypot(face[0], face[1]) or 1.0
    fx, fy = face[0] / fl, face[1] / fl
    yaw = math.atan2(fy, fx) + math.pi / 2
    cs, sn = math.cos(yaw), math.sin(yaw)

    def part(sx_, sy_, sz_, lx, ly, lz, pl, tilt=0.0):
        box(sx_, sy_, sz_, (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, lz),
            pl, yaw=yaw, tilt=tilt)

    jh = h * 0.55
    part(frame, depth, jh, -w / 2 + frame / 2, 0, z0 + jh / 2, pool)
    part(frame, depth, jh, w / 2 - frame / 2, 0, z0 + jh / 2, pool)
    NSEG = 9
    for i in range(NSEG):
        t0 = i / NSEG; t1 = (i + 1) / NSEG
        x0 = -w / 2 + w * t0; x1 = -w / 2 + w * t1
        r0 = z0 + jh + ogee(t0) * (h - jh); r1 = z0 + jh + ogee(t1) * (h - jh)
        seg_l = math.hypot(x1 - x0, r1 - r0) + frame * 0.4
        part(seg_l, depth, frame, (x0 + x1) / 2, 0, (r0 + r1) / 2, pool,
             tilt=math.atan2(r0 - r1, x1 - x0))
    if lit is not None:
        if lit:
            # His order: no bright panels - windows are EMPTY, screened by an
            # Arabian lattice. Turned-wood bars fill the opening to just below
            # the spring of the arch; the pointed head stays open dark.
            gw = w - frame * 1.3
            gh = jh + (h - jh) * 0.45 - frame * 0.2
            ly = -depth * 0.5 + 0.30
            nv = max(2, int(gw / 0.30))
            for iv in range(1, nv):
                lx = -gw / 2 + gw * iv / nv
                part(0.065, 0.065, gh, lx, ly, z0 + gh / 2 + 0.05, wood)
            nh = max(2, int(gh / 0.50))
            for ih in range(1, nh):
                part(gw, 0.055, 0.055, 0, ly, z0 + gh * ih / nh + 0.05, wood)
            # the sill ties the screen into the stone
            part(gw + frame * 0.6, 0.35, 0.18, 0, ly, z0 + 0.02, pool)
        else:
            ph = h * 0.97 - frame * 0.3
            part(w - frame * 1.3, 0.25, ph, 0, -depth * 0.5 + 0.24,
                 z0 + ph / 2 + frame * 0.15, stone)


def wood_window(cx, cy, z0, w, h, depth, face=(0, -1)):
    """His order: the wooden treatment from the oriels on every window of
    the second storey, outside and in. A timber surround proud of the wall,
    the pointed arch framed in wood, the light behind."""
    fl = math.hypot(face[0], face[1]) or 1.0
    fx, fy = face[0] / fl, face[1] / fl
    yaw = math.atan2(fy, fx) + math.pi / 2
    cs, sn = math.cos(yaw), math.sin(yaw)
    lx, ly = 0, depth * 0.28
    box(w + 1.0, 0.45, h + 0.8, (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs,
        z0 + (h + 0.8) / 2 - 0.25), wood, yaw=yaw)
    arch(cx, cy, z0, w, h, depth, wood, frame=0.42, face=face, lit=True)


def door_leaves(cx, cy, z0, w, h, face=(0, -1), ajar=0.55, inset=0.16):
    """The double door, recorded as DATA: the engine hangs the leaves and
    swings them at a touch. Nothing static is baked any more."""
    fl0 = math.hypot(face[0], face[1]) or 1.0
    DOORS.append({"x": round(cx, 2), "z": round(-cy, 2), "y0": round(z0, 2),
                  "w": round(w - inset * 2, 2), "h": round(h - 0.25, 2),
                  "fx": round(face[0] / fl0, 3), "fz": round(-face[1] / fl0, 3)})
    return


def _door_leaves_retired(cx, cy, z0, w, h, face=(0, -1), ajar=0.55, inset=0.16):
    """kept for reference"""
    fl = math.hypot(face[0], face[1]) or 1.0
    fx, fy = face[0] / fl, face[1] / fl
    yaw = math.atan2(fy, fx) + math.pi / 2
    cs, sn = math.cos(yaw), math.sin(yaw)
    w = w - inset * 2
    lw = w / 2 - 0.05
    lh = h - 0.25
    for side in (-1, 1):
        hx0, hy0 = cx + (side * w / 2) * cs, cy + (side * w / 2) * sn
        swing = yaw + side * ajar
        c2, s2 = math.cos(swing), math.sin(swing)
        mx = hx0 + (-side * lw / 2) * c2
        my = hy0 + (-side * lw / 2) * s2
        box(lw, 0.13, lh, (mx, my, z0 + lh / 2), wood, yaw=swing)
        for st in (0.18, 0.5, 0.82):
            box(lw - 0.16, 0.05, 0.16, (mx + 0.10 * (-s2), my + 0.10 * c2,
                z0 + lh * st), gold, yaw=swing)
        for gx in (-0.3, 0.3):
            for gz in (0.32, 0.62):
                box(0.09, 0.07, 0.09, (mx + gx * lw * 0.5 * c2 + 0.10 * (-s2),
                    my + gx * lw * 0.5 * s2 + 0.10 * c2, z0 + lh * gz), gold, yaw=swing)


def arch_row(x0, x1, y, z0, n, w, h, depth, pool, lit=True, face=(0, -1)):
    for i in range(n):
        cx = x0 + (x1 - x0) * (i + 0.5) / n
        arch(cx, y, z0, w, h, depth, pool, lit=lit, face=face)


def cornice(hx, hy, z, pool, lip=0.7):
    box(hx * 2 + lip * 2, hy * 2 + lip * 2, lip * 0.9, (0, 0, z), pool)


def dentils(cx, cy, hx, hy, z, pool, step=1.6):
    """A corbel course under a cornice: the small teeth that catch the light
    and stop a big wall reading as a slab."""
    n = max(2, int(hx * 2 / step))
    for i in range(n):
        x = cx - hx + (2 * hx) * (i + 0.5) / n
        box(0.6, 0.5, 0.55, (x, cy - hy - 0.25, z), pool)
        box(0.6, 0.5, 0.55, (x, cy + hy + 0.25, z), pool)
    m = max(2, int(hy * 2 / step))
    for i in range(m):
        y = cy - hy + (2 * hy) * (i + 0.5) / m
        box(0.5, 0.6, 0.55, (cx - hx - 0.25, y, z), pool)
        box(0.5, 0.6, 0.55, (cx + hx + 0.25, y, z), pool)


def parapet(cx, cy, hx, hy, z, pool, hh=1.3):
    box(hx * 2, 0.7, hh, (cx, cy - hy, z + hh / 2), pool)
    box(hx * 2, 0.7, hh, (cx, cy + hy, z + hh / 2), pool)
    box(0.7, hy * 2, hh, (cx - hx, cy, z + hh / 2), pool)
    box(0.7, hy * 2, hh, (cx + hx, cy, z + hh / 2), pool)
    n = int(hx)
    for i in range(n):
        x = cx - hx + (2 * hx) * (i + 0.5) / n
        for sy in (-1, 1):
            box(0.9, 0.75, hh * 0.55, (x, cy + sy * hy, z + hh + hh * 0.27), pool)
            # a pyramid tip on every merlon: the skyline stops being a comb
            cyl(0.5, 0.5, (x, cy + sy * hy, z + hh + hh * 0.55 + 0.25), pool,
                verts=4, r_top=0.05, smooth=False)


def string_course(cx, cy, hx, hy, z, pool):
    box(hx * 2 + 0.7, hy * 2 + 0.7, 0.4, (cx, cy, z), pool)


def minaret(cx, cy, htot):
    """Hollow shaft, door, spiral stair round a newel, railed lantern stage
    with a burning lantern, sapphire cap."""
    r = 3.1
    wall_t = 0.55
    lz = 2.2 + htot * 0.82
    NW = 14
    for k in range(NW):
        a = (k + 0.5) / NW * 2 * math.pi - math.pi / 2
        if abs(a + math.pi / 2) < 0.5:
            continue
        seg_w = 2 * math.pi * r * 1.5 / NW * 1.25
        box(seg_w, 0.8, 2.2, (cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r * 1.5, 1.1),
            stone, yaw=a + math.pi / 2)
        col(cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r * 1.5, 1.1,
            seg_w / 2 + 0.1, seg_w / 2 + 0.1, 1.1)
    arch(cx, cy - r * 1.5 - 0.3, 0.0, 2.2, 3.6, 0.8, stone, frame=0.4, lit=None)
    door_leaves(cx, cy - r * 1.5 - 0.15, 0.0, 1.8, 2.9, face=(0, -1), ajar=0.85)
    shaft_h = lz - 2.2
    for k in range(NW):
        a = (k + 0.5) / NW * 2 * math.pi - math.pi / 2
        seg_w = 2 * math.pi * r / NW * 1.25
        if abs(a + math.pi / 2) < 0.5:
            box(seg_w, wall_t, shaft_h - 3.6,
                (cx + math.cos(a) * r, cy + math.sin(a) * r, 2.2 + 3.6 + (shaft_h - 3.6) / 2),
                stone, yaw=a + math.pi / 2)
        else:
            box(seg_w, wall_t, shaft_h,
                (cx + math.cos(a) * r, cy + math.sin(a) * r, 2.2 + shaft_h / 2),
                stone, yaw=a + math.pi / 2)
        col(cx + math.cos(a) * r, cy + math.sin(a) * r, 2.2 + shaft_h / 2,
            seg_w / 2 + 0.08, seg_w / 2 + 0.08, shaft_h / 2)
    for sz_ in range(4):
        zz = 2.2 + shaft_h * (0.22 + 0.19 * sz_)
        arch(cx, cy - r - 0.15, zz, 0.9, 2.2, 0.5, stone, frame=0.22, lit=True)
    for bz in (htot * 0.42, htot * 0.62):
        cyl(r * 1.45, 0.9, (cx, cy, 2.2 + bz), stone, verts=16)
        cyl(r * 1.28, 1.6, (cx, cy, 2.2 + bz + 1.2), stone, verts=16)
    box(4.6, 4.6, 0.4, (cx, cy, 0.2), stone)
    col(cx, cy, 0.2, 2.3, 2.3, 0.2)
    cyl(0.55, shaft_h + 1.8, (cx, cy, 0.4 + (shaft_h + 1.8) / 2), stone, verts=12)
    n_steps = int((shaft_h + 1.6) / 0.30)
    for i in range(n_steps):
        a = i * 0.42 - math.pi / 2
        sx_ = cx + math.cos(a) * 1.45
        sy_ = cy + math.sin(a) * 1.45
        sz2 = 0.62 + i * 0.30
        box(1.7, 0.72, 0.22, (sx_, sy_, sz2), stone, yaw=a + math.pi / 2)
        col(sx_, sy_, sz2, 0.85, 0.85, 0.12)
    cyl(r * 1.1, 0.8, (cx, cy, lz), stone, verts=16)
    col(cx, cy, lz, r * 1.1, r * 1.1, 0.4)
    cyl(r * 1.12, 1.0, (cx, cy, lz + 0.9), stone, verts=16)
    for i in range(8):
        a = i / 8 * 2 * math.pi
        box(0.55, 0.55, 3.4, (cx + math.cos(a) * r * 0.88, cy + math.sin(a) * r * 0.88, lz + 1.9), stone)
    cyl(0.09, 1.1, (cx, cy, lz + 3.1), gold, verts=8)
    box(0.5, 0.5, 0.9, (cx, cy, lz + 2.25), glow)
    box(0.62, 0.62, 0.12, (cx, cy, lz + 2.82), gold)
    box(0.62, 0.62, 0.12, (cx, cy, lz + 1.72), gold)
    cyl(r * 1.18, 0.8, (cx, cy, lz + 3.9), stone, verts=16)
    dome(cx, cy, lz + 4.3, r * 1.0, r * 2.1, ribs=12, drum=False)


# ================================================================ THE CENTRE
S1_H, S2_H, S3_H, S4_H, S5_H, S6_H = 11.0, 8.0, 7.0, 6.0, 7.0, 6.0
z1, z2, z3, z4, z5, z6 = 0.0, 11.0, 19.0, 26.0, 32.0, 39.0
z7 = z6 + S6_H

# S1 - THE GATE AND THE HALL (real interior; the door is open)
box(48, 36, 2.0, (0, 0, 1.0), stone)
col(0, 0, 1.0, 24, 18, 1.0)
box(46, 34, 0.6, (0, 0, 2.05), stone)
col(0, 0, 2.05, 23, 17, 0.3)
WT = 1.7
for sxw in (-1, 1):
    box(20.4, WT, S1_H - 2.3, (sxw * (2.8 + 10.2), 17 - WT / 2, 2.3 + (S1_H - 2.3) / 2), stone)
    col(sxw * 13.0, 17 - WT / 2, S1_H / 2, 10.2, WT / 2, S1_H / 2)
box(5.6, WT, S1_H - 2.3 - 9.2, (0, 17 - WT / 2, 2.3 + 9.2 + (S1_H - 2.3 - 9.2) / 2), stone)
arch(0, 17.4, 2.3, 5.4, 8.8, 0.9, stone, frame=0.55, lit=None, face=(0, 1))
door_leaves(0, 17.6, 2.35, 4.8, 6.4, face=(0, 1), ajar=0.66)
for sxw in (-1, 1):
    box(WT, 34, S1_H - 2.3, (sxw * (23 - WT / 2), 0, 2.3 + (S1_H - 2.3) / 2), stone)
    col(sxw * (23 - WT / 2), 0, S1_H / 2, WT / 2, 17, S1_H / 2)
for sxw in (-1, 1):
    box(20.4, WT, S1_H - 2.3, (sxw * (2.8 + 10.2), -17 + WT / 2, 2.3 + (S1_H - 2.3) / 2), stone)
    col(sxw * 13.0, -17 + WT / 2, S1_H / 2, 10.2, WT / 2, S1_H / 2)
box(5.6, WT, S1_H - 2.3 - 9.2, (0, -17 + WT / 2, 2.3 + 9.2 + (S1_H - 2.3 - 9.2) / 2), stone)
box(46, 34, 0.9, (0, 0, z1 + S1_H - 0.45), stone)
for bx in range(-3, 4):
    box(1.1, 30.5, 0.9, (bx * 6.2, 0, z1 + S1_H - 1.25), wood)
for sxc in (-1, 1):
    for cyc in (-10.5, -3.5, 3.5, 10.5):
        cyl(1.05, S1_H - 3.4, (sxc * 8.5, cyc, 2.3 + (S1_H - 3.4) / 2), stone, verts=14)
        cyl(1.35, 0.7, (sxc * 8.5, cyc, S1_H - 1.35), stone, verts=14)
        col(sxc * 8.5, cyc, S1_H / 2, 1.1, 1.1, S1_H / 2)
for lyc in (-11, -4.5, 2, 8.5):
    cyl(0.09, 2.6, (0, lyc, z1 + S1_H - 2.6), gold, verts=8)
    box(0.5, 0.5, 0.9, (0, lyc, z1 + S1_H - 4.2), glow)
    box(0.62, 0.62, 0.12, (0, lyc, z1 + S1_H - 3.62), gold)
    box(0.62, 0.62, 0.12, (0, lyc, z1 + S1_H - 4.85), gold)
box(5.4, 26, 0.14, (0, -1, 2.42), rug)      # the hall's runner
cornice(23, 17, z1 + S1_H, stone)
dentils(0, 0, 23, 17, z1 + S1_H - 0.7, stone)
# the iwan: hollow portal, telescoping rings, open lit-from-within door
for sxw in (-1, 1):
    box(4.6, 4.2, 17.5, (sxw * 5.2, -17.5, 8.75), stone)
    col(sxw * 5.2, -17.5, 8.75, 2.3, 2.1, 8.75)
box(15, 4.2, 17.5 - 10.4, (0, -17.5, 10.4 + (17.5 - 10.4) / 2), stone)
arch(0, -20.9, 0.6, 9.0, 14.5, 2.8, stone, frame=1.5, lit=None)
for i, (mw, mh) in enumerate(((7.6, 13.4), (6.4, 12.4), (5.2, 11.4))):
    arch(0, -21.6 + 0.5 * i, 0.6, mw, mh, 0.6, stone, frame=0.58, lit=None)
arch(0, -19.9, 0.6, 5.6, 9.2, 0.7, stone, frame=0.5, lit=None)
door_leaves(0, -19.6, 2.35, 5.0, 6.8, face=(0, -1), ajar=0.72)
# the landing: the strip between the top tread and the plinth had no floor -
# the very hole he fell into under the entrance door
box(9.4, 3.0, 2.35, (0, -19.3, 2.35 / 2), stone)
col(0, -19.3, 2.35 / 2, 4.7, 1.5, 2.35 / 2)
# the grand stair: the hall floor stood 2.35 m above the approach with
# nothing to climb - eight solid treads from the ground to the gate
for i_st in range(8):
    st_h = 2.35 - i_st * 0.29
    st_y = -19.9 - 0.62 * (i_st + 1)
    box(9.4, 0.66, st_h, (0, st_y, st_h / 2), stone)
    col(0, st_y, st_h / 2, 4.7, 0.33, st_h / 2)
arch_row(-21, -9, -17.2, 1.6, 3, 2.6, 6.5, 1.0, stone, lit=True)
arch_row(9, 21, -17.2, 1.6, 3, 2.6, 6.5, 1.0, stone, lit=True)
for sx in (-1, 1):
    for i in range(4):
        cy1 = -12 + 24 * (i + 0.5) / 4
        arch(sx * 23.25, cy1, 1.6, 2.6, 6.5, 1.0, stone, lit=True, face=(sx, 0))
arch_row(-14, 14, 17.25, 1.6, 5, 2.6, 6.5, 1.0, stone, lit=True, face=(0, 1))

# S2 - THE ARCADE
box(42, 30, S2_H, (0, 0, z2 + S2_H / 2), stone)
for i in range(7):
    cxw = -19 + 38 * (i + 0.5) / 7
    wood_window(cxw, -15.35, z2 + 0.8, 3.4, 6.2, 1.2)
    wood_window(cxw, 15.35, z2 + 0.8, 3.4, 6.2, 1.2, face=(0, 1))
for sx in (-1, 1):
    for i in range(5):
        cy2 = -12 + 24 * (i + 0.5) / 5
        wood_window(sx * 21.35, cy2, z2 + 0.8, 3.2, 6.0, 1.2, face=(sx, 0))
cornice(21, 15, z2 + S2_H, stone)
dentils(0, 0, 21, 15, z2 + S2_H - 0.7, stone)
col(0, 0, z2 + S2_H / 2, 21, 15, S2_H / 2)

# S3 - THE MASHRABIYA (arched wooden oriels)
box(38, 27, S3_H, (0, 0, z3 + S3_H / 2), stone)
for sx in (-1, 1):
    for cy3 in (-8, 0, 8):
        box(2.2, 6.0, 5.6, (sx * 19.6, cy3, z3 + 3.3), wood)
        for wy in (-1.4, 1.4):
            arch(sx * 20.75, cy3 + wy, z3 + 1.1, 1.5, 3.9, 0.5, wood,
                 frame=0.3, lit=True, face=(sx, 0))
for cx3 in (-14.4, 0, 14.4):
    box(6.0, 2.2, 5.6, (cx3, -14.1, z3 + 3.3), wood)
    for wx in (-1.5, 1.5):
        arch(cx3 + wx, -15.25, z3 + 1.1, 1.5, 3.9, 0.5, wood,
             frame=0.3, lit=True, face=(0, -1))
cornice(19, 13.5, z3 + S3_H, stone)
dentils(0, 0, 19, 13.5, z3 + S3_H - 0.7, stone)
col(0, 0, z3 + S3_H / 2, 19, 13.5, S3_H / 2)

# S4 - THE BAND
box(34, 24, S4_H, (0, 0, z4 + S4_H / 2), stone)
arch_row(-14, 14, -12.35, z4 + 0.8, 8, 1.9, 4.4, 1.0, stone, lit=True)
arch_row(-14, 14, 12.35, z4 + 0.8, 8, 1.9, 4.4, 1.0, stone, lit=True, face=(0, 1))
for sx in (-1, 1):
    for i in range(4):
        cy4 = -9 + 18 * (i + 0.5) / 4
        arch(sx * 17.35, cy4, z4 + 0.8, 1.9, 4.4, 1.0, stone, lit=True, face=(sx, 0))
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl(2.0, S4_H + S5_H + 2, (sx * 16, sy * 11, z4 + (S4_H + S5_H) / 2), stone, verts=12)
        cyl(2.3, 0.8, (sx * 16, sy * 11, z4 + S4_H + S5_H + 2.2), stone, verts=12)
        dome(sx * 16, sy * 11, z4 + S4_H + S5_H + 2.5, 2.15, 4.1, ribs=10, drum=False,
             shell=gold if GOLDSMALL else None)
cornice(17, 12, z4 + S4_H, stone)
col(0, 0, z4 + S4_H / 2, 17, 12, S4_H / 2)

# S5 - THE OCTAGON
r5o = 15.0
ring_a = []
ring_b = []
for i in range(8):
    a5 = (i + 0.5) / 8 * 2 * math.pi
    ring_a.append(len(stone.v))
    stone.v.append((math.cos(a5) * r5o, math.sin(a5) * r5o * 0.78, z5))
for i in range(8):
    a5 = (i + 0.5) / 8 * 2 * math.pi
    ring_b.append(len(stone.v))
    stone.v.append((math.cos(a5) * r5o * 0.92, math.sin(a5) * r5o * 0.92 * 0.78, z5 + S5_H))
for i in range(8):
    j = (i + 1) % 8
    stone.quad(ring_a[i], ring_a[j], ring_b[j], ring_b[i])
stone.f.append(tuple(reversed(ring_a))); stone.smooth.append(False)
stone.f.append(tuple(ring_b)); stone.smooth.append(False)
for i in range(8):
    a5 = (i + 0.5) / 8 * 2 * math.pi
    fx, fy = math.cos(a5), math.sin(a5)
    arch(fx * r5o * 0.96, fy * r5o * 0.78 * 0.96, z5 + 0.9, 2.6, 4.6, 0.9, stone,
         frame=0.42, lit=True, face=(fx, fy))
col(0, 0, z5 + S5_H / 2, 14, 11, S5_H / 2)

# S6 - THE DRUM GALLERY
cyl(12.5, S6_H, (0, 0, z6 + S6_H / 2), stone, verts=40)
for i in range(12):
    a6 = i / 12 * 2 * math.pi
    fx, fy = math.cos(a6), math.sin(a6)
    arch(fx * 12.7, fy * 12.7, z6 + 0.9, 2.1, 4.2, 0.9, stone, frame=0.4, lit=True, face=(fx, fy))
cyl(13.4, 0.9, (0, 0, z6 + S6_H + 0.2), gold, verts=40)
col(0, 0, z6 + S6_H / 2, 12.5, 12.5, S6_H / 2)

# S7 - THE CROWN
dome(0, 0, z7, 11.0, 21.0, ribs=20)
for sx in (-1, 1):
    for sy in (-1, 1):
        dome(sx * 8.5, sy * 8.5, z7 - 1.2, 2.6, 4.8, ribs=10,
             shell=gold if GOLDSMALL else None)

# ============================================================ THE COMPOUND
def module(cx, cy, face, gate=False):
    """One curtain block. The outward face carries the arcades as before;
    the COURT face now carries its own lit arches, niches and dentils - his
    order: the inner walls must have flavour too."""
    ox, oy = face
    ax, ay = -oy, ox
    inward = (-ox, -oy)
    w_hx, w_hy = 15.0, 13.0
    W1, W2, W3 = 8.5, 7.0, 6.0

    def P(a, o):
        return (cx + a * ax + o * ox, cy + a * ay + o * oy)

    def sized(a_len, o_len):
        return (abs(a_len * ax) + abs(o_len * ox), abs(a_len * ay) + abs(o_len * oy))

    # THE GROUND STOREY IS HOLLOW: a room behind a court door - or, for a
    # gate module, a passage straight through the curtain into the court.
    # Storeys above stay solid and ride on the room's ceiling.
    WT2 = 2.0
    fl_z = 2.1                                  # room floor top, one shallow step below the paving
    ceil_z = W1 - 0.9                           # room ceiling underside
    sx_, sy_ = sized(w_hx * 2 + 1.4, w_hy * 2 + 1.4)
    box(sx_, sy_, 1.6, (cx, cy, 0.8), stone)                       # plinth
    col(cx, cy, 0.8, sx_ / 2, sy_ / 2, 0.8)
    fx_, fy_ = sized(w_hx * 2, w_hy * 2)
    box(fx_, fy_, 0.5, (cx, cy, 1.55 + 0.25), stone)               # room floor
    col(cx, cy, 1.8, fx_ / 2, fy_ / 2, 0.25)
    box(fx_, fy_, 0.9, (cx, cy, ceil_z + 0.45), stone)             # ceiling
    # side walls (the two along-walls)
    for sa in (-1, 1):
        wx_, wy_ = P(sa * (w_hx - WT2 / 2), 0)
        ssx, ssy = sized(WT2, w_hy * 2)
        box(ssx, ssy, ceil_z - fl_z, (wx_, wy_, fl_z + (ceil_z - fl_z) / 2), stone)
        col(wx_, wy_, (fl_z + ceil_z) / 2, ssx / 2, ssy / 2, (ceil_z - fl_z) / 2)
    if gate:
        # a PASSAGE: outward wall and court wall both open, straight through
        for oo in (w_hy - WT2 / 2, -(w_hy - WT2 / 2)):
            for sa in (-1, 1):
                wx_, wy_ = P(sa * (w_hx / 2 + 1.35), oo)
                ssx, ssy = sized(w_hx - 2.7, WT2)
                box(ssx, ssy, ceil_z - fl_z, (wx_, wy_, fl_z + (ceil_z - fl_z) / 2), stone)
                col(wx_, wy_, (fl_z + ceil_z) / 2, ssx / 2, ssy / 2, (ceil_z - fl_z) / 2)
            lx_, ly_ = P(0, oo)
            lsx, lsy = sized(5.4, WT2)
            box(lsx, lsy, ceil_z - fl_z - 4.9, (lx_, ly_, fl_z + 4.9 + (ceil_z - fl_z - 4.9) / 2), stone)
        dx_, dy_ = P(0, -(w_hy - 0.7))
        door_leaves(dx_, dy_, fl_z, 4.4, 4.6, face=inward, ajar=0.78)
    else:
        # a ROOM: outward wall solid, court wall opens through a door
        wx_, wy_ = P(0, w_hy - WT2 / 2)
        ssx, ssy = sized(w_hx * 2, WT2)
        box(ssx, ssy, ceil_z - fl_z, (wx_, wy_, fl_z + (ceil_z - fl_z) / 2), stone)
        col(wx_, wy_, (fl_z + ceil_z) / 2, ssx / 2, ssy / 2, (ceil_z - fl_z) / 2)
        for sa in (-1, 1):
            wx_, wy_ = P(sa * (w_hx / 2 + 1.6), -(w_hy - WT2 / 2))
            ssx, ssy = sized(w_hx - 3.2, WT2)
            box(ssx, ssy, ceil_z - fl_z, (wx_, wy_, fl_z + (ceil_z - fl_z) / 2), stone)
            col(wx_, wy_, (fl_z + ceil_z) / 2, ssx / 2, ssy / 2, (ceil_z - fl_z) / 2)
        lx_, ly_ = P(0, -(w_hy - WT2 / 2))
        lsx, lsy = sized(6.4, WT2)
        box(lsx, lsy, ceil_z - fl_z - 4.4, (lx_, ly_, fl_z + 4.4 + (ceil_z - fl_z - 4.4) / 2), stone)
        adx, ady = P(0, -(w_hy + 0.28))
        arch(adx, ady, fl_z, 3.2, 4.6, 0.9, stone, frame=0.45, lit=None, face=inward)
        dlx, dly = P(0, -(w_hy - 0.75))
        door_leaves(dlx, dly, fl_z, 2.9, 4.0, face=inward, ajar=0.62)
        # the room dressed: a runner, two hanging lanterns, lit niches
        rx_, ry_ = P(0, 0)
        rsx, rsy = sized(3.2, w_hy * 1.2)
        box(rsx, rsy, 0.1, (rx_, ry_, fl_z + 0.3), rug)
        for ll in (-4.5, 4.5):
            llx, lly = P(ll, 0)
            cyl(0.07, 1.6, (llx, lly, ceil_z - 1.6), gold, verts=8)
            box(0.44, 0.44, 0.8, (llx, lly, ceil_z - 2.75), glow)
            box(0.56, 0.56, 0.1, (llx, lly, ceil_z - 2.24), gold)
            box(0.56, 0.56, 0.1, (llx, lly, ceil_z - 3.3), gold)
        for nn in (-8, 0, 8):
            nx_, ny_ = P(nn, w_hy - WT2 - 0.02)
            arch(nx_, ny_, fl_z + 0.9, 1.7, 3.3, 0.6, stone, frame=0.3,
                 lit=(nn == 0), face=inward)
    # the upper storeys ride on the ceiling, solid as before
    for (hw, hd, zz, hh) in ((w_hx, w_hy, W1, 0), (w_hx - 1, w_hy - 1, W1, W2),
                             (w_hx - 2, w_hy - 2, W1 + W2, W3)):
        if hh <= 0:
            continue
        ssx, ssy = sized(hw * 2, hd * 2)
        box(ssx, ssy, hh, (cx, cy, zz + hh / 2), stone)
        string_course(cx, cy, ssx / 2, ssy / 2, zz + hh - 0.1, stone)
    # the ground storey's outer shell above the openings, so the outside
    # face still reads as one wall (a band between ceiling and first floor)
    bsx, bsy = sized(w_hx * 2, w_hy * 2)
    box(bsx, bsy, W1 - ceil_z - 0.9, (cx, cy, ceil_z + 0.9 + (W1 - ceil_z - 0.9) / 2), stone)
    string_course(cx, cy, bsx / 2, bsy / 2, W1 - 0.1, stone)
    col(cx, cy, (W1 + W2 + W3 + fl_z) / 2 + 2, bsx / 2, bsy / 2, (W1 + W2 + W3 - fl_z) / 2 - 2)

    inward = (-ox, -oy)
    if gate:
        # the gate tower is a PORTAL, not a plug: two flanks and a brow,
        # the passage running clean between them
        for gfs in (-1, 1):
            fgx, fgy = P(gfs * 3.48, w_hy + 0.6)
            fsx, fsy = sized(1.55, 3.4)
            box(fsx, fsy, 10.5, (fgx, fgy, 5.25), stone)
            col(fgx, fgy, 5.25, fsx / 2, fsy / 2, 5.25)
        bgx, bgy = P(0, w_hy + 0.6)
        bsx, bsy = sized(8.5, 3.4)
        box(bsx, bsy, 10.5 - 6.2, (bgx, bgy, 6.2 + (10.5 - 6.2) / 2), stone)
        agx, agy = P(0, w_hy + 2.45)
        arch(agx, agy, 0.5, 4.6, 8.2, 2.2, stone, frame=0.65, lit=None, face=face)
        for sa in (-1, 1):
            for i in range(2):
                aa = sa * (6 + i * 4.2)
                axp, ayp = P(aa, w_hy + 0.35)
                arch(axp, ayp, 1.4, 2.2, 5.2, 1.0, stone, lit=True, face=face)
    else:
        for i in range(4):
            aa = -11.2 + 22.4 * (i + 0.5) / 4
            axp, ayp = P(aa, w_hy + 0.35)
            arch(axp, ayp, 1.4, 2.4, 5.6, 1.0, stone, lit=True, face=face)
    for i in range(5):
        aa = -12 + 24 * (i + 0.5) / 5
        axp, ayp = P(aa, w_hy - 1 + 0.35)
        wood_window(axp, ayp, W1 + 0.8, 2.4, 4.6, 1.0, face=face)
    for i in range(4):
        aa = -10 + 20 * (i + 0.5) / 4
        axp, ayp = P(aa, w_hy - 2 + 0.35)
        arch(axp, ayp, W1 + W2 + 0.8, 2.2, 4.0, 1.0, stone, lit=True, face=face)

    # THE COURT FACE: lit arches on two storeys, a niche band, dentils
    for i in range(4):
        aa = -11 + 22 * (i + 0.5) / 4
        axp, ayp = P(aa, -(w_hy + 0.35))
        arch(axp, ayp, 1.2, 2.4, 5.4, 1.0, stone, lit=True, face=inward)
    for i in range(3):
        aa = -8 + 16 * (i + 0.5) / 3
        axp, ayp = P(aa, -(w_hy - 1 + 0.35))
        wood_window(axp, ayp, W1 + 0.9, 2.2, 4.4, 1.0, face=inward)
    for i in range(5):
        aa = -10 + 20 * (i + 0.5) / 5
        axp, ayp = P(aa, -(w_hy - 2 + 0.30))
        arch(axp, ayp, W1 + W2 + 1.0, 1.5, 3.2, 0.8, stone, lit=(i % 2 == 0), face=inward)
    dsx, dsy = sized(w_hx - 0.5, w_hy - 0.5)
    dentils(cx, cy, dsx, dsy, W1 - 0.55, stone)

    parapet(cx, cy, sized(w_hx - 2.3, w_hy - 2.3)[0], sized(w_hx - 2.3, w_hy - 2.3)[1],
            W1 + W2 + W3, stone)
    dome(cx, cy, W1 + W2 + W3, 5.2, 9.5, ribs=14, seg=36)
    for sa in (-1, 1):
        ex, ey = P(sa * 9.5, 0)
        sphere(1.5, (ex, ey, W1 + W2 + W3 + 1.7), gold if GOLDSMALL else sapph,
               seg=14, rings=9, zscale=1.35)


def corner_tower(cx, cy):
    H = 30.0
    cyl(10.2, 2.0, (cx, cy, 1.0), stone, verts=8, smooth=False)
    # the ground five metres are a ROOM: eight wall segments with a door
    # gap toward the court diagonal, a floor, and the shaft solid above
    droom_h = 5.2
    da = math.atan2(62 - cy, 0 - cx)              # the door faces the court
    for k in range(8):
        a8 = (k + 0.5) / 8 * 2 * math.pi
        if abs(((a8 - da + math.pi) % (2 * math.pi)) - math.pi) < 0.42:
            continue
        seg_w = 2 * math.pi * 8.4 / 8 * 1.18
    # walls sit at r 8.4, 1.2 thick; the cylinder above closes the drum
        box(seg_w, 1.2, droom_h, (cx + math.cos(a8) * 8.4, cy + math.sin(a8) * 8.4, 2.0 + droom_h / 2),
            stone, yaw=a8 + math.pi / 2)
        col(cx + math.cos(a8) * 8.4, cy + math.sin(a8) * 8.4, 2.0 + droom_h / 2,
            seg_w / 2 + 0.1, seg_w / 2 + 0.1, droom_h / 2)
    box(16, 16, 0.5, (cx, cy, 2.05), stone)
    col(cx, cy, 2.05, 8, 8, 0.3)
    cyl(10.2, 2.0, (cx, cy, 1.0), stone, verts=8, smooth=False)
    col(cx, cy, 1.0, 7.2, 7.2, 1.0)
    arch(cx + math.cos(da) * 9.0, cy + math.sin(da) * 9.0, 2.0, 2.6, 4.2, 1.0,
         stone, frame=0.45, lit=None, face=(math.cos(da), math.sin(da)))
    door_leaves(cx + math.cos(da) * 8.6, cy + math.sin(da) * 8.6, 2.0, 2.3, 3.6,
                face=(math.cos(da), math.sin(da)), ajar=0.7)
    for ll in (-3.5, 3.5):
        cyl(0.07, 1.4, (cx + ll, cy, 2.0 + droom_h - 1.4), gold, verts=8)
        box(0.44, 0.44, 0.75, (cx + ll, cy, 2.0 + droom_h - 2.5), glow)
        box(0.56, 0.56, 0.1, (cx + ll, cy, 2.0 + droom_h - 2.02), gold)
    cyl(9.0, H - droom_h, (cx, cy, 2.0 + droom_h + (H - droom_h) / 2), stone, verts=8, smooth=False)
    for i in range(8):
        a8 = (i + 0.5) / 8 * 2 * math.pi
        fx8, fy8 = math.cos(a8), math.sin(a8)
        arch(cx + fx8 * 9.1, cy + fy8 * 9.1, H - 6.5, 2.2, 4.6, 0.9, stone,
             frame=0.4, lit=True, face=(fx8, fy8))
        arch(cx + fx8 * 9.1, cy + fy8 * 9.1, H * 0.35, 1.8, 3.6, 0.7, stone,
             frame=0.35, lit=False, face=(fx8, fy8))
    cyl(9.9, 1.2, (cx, cy, 2.0 + H + 0.4), stone, verts=8, smooth=False)
    parapet(cx, cy, 7.4, 7.4, 2.0 + H + 1.0, stone, hh=1.1)
    dome(cx, cy, 2.0 + H + 1.0, 6.0, 11.0, ribs=14, seg=40)
    col(cx, cy, (2.0 + droom_h + H) / 2 + 1, 9.4, 9.4, (H - droom_h) / 2 + 1)


def connector(x0, y0, x1, y1, h=7.5):
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy) or 1.0
    yaw = math.atan2(dy, dx)
    box(ln + 1.5, 1.6, h * 0.45, (mx, my, h * 0.55 + h * 0.225), stone, yaw=yaw)
    fx9, fy9 = -dy / ln, dx / ln
    arch(mx, my, 0.4, min(3.2, ln * 0.55 + 1.2), h * 0.62, 1.6, stone, frame=0.5,
         lit=None, face=(fx9, fy9))
    col(mx, my, h * 0.5, abs(dx) / 2 + 0.8, abs(dy) / 2 + 0.8, h * 0.5)


for sxm in (-1, 1):
    for i in range(3):
        module(sxm * (38 + 30 * i), 0, (0, -1), gate=(i == 0))
for i in range(5):
    for sxm in (-1, 1):
        module(sxm * 100, 12 + 30 * i, (sxm, 0))
for i in range(7):
    module(-90 + 30 * i, 120, (0, 1), gate=(i == 3))

for sxm in (-1, 1):
    corner_tower(sxm * 109, -19)
    corner_tower(sxm * 109, 129)

for sxm in (-1, 1):
    minaret(sxm * 23, -24, 58.0)
    minaret(sxm * 120, 75, 52.0)
    connector(sxm * 113, 75, sxm * 118, 75)
    minaret(sxm * 23, 140, 52.0)
    connector(sxm * 23, 133, sxm * 23, 138)

# ============================================================ THE COURT
# paved now, not bare ground - and SOLID
box(174, 90, 0.5, (0, 62, 2.25), stone)
col(0, 62, 2.25, 87, 45, 0.25)
RW_D = 5.5

def riwaq_run(x0, y0, x1, y1, face):
    """Taller, slimmer arches than v1: the haram rhythm."""
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    fx0, fy0 = face
    n = max(2, int(ln / 4.2))
    for i in range(n + 1):
        px = x0 + ux * (ln * i / n)
        py = y0 + uy * (ln * i / n)
        cyl(0.5, 7.2, (px, py, 2.5 + 3.6), stone, verts=10)
        col(px, py, 6.1, 0.55, 0.55, 3.6)
    for i in range(n):
        px = x0 + ux * (ln * (i + 0.5) / n)
        py = y0 + uy * (ln * (i + 0.5) / n)
        arch(px, py, 2.5, ln / n - 0.8, 7.2, 0.7, stone, frame=0.38, lit=None, face=face)
    # The roof of the colonnade runs INTO the curtain behind it. It used to
    # stop at its own depth and left a hairline of daylight along the joint;
    # a roof that only kisses a wall always will. It is carried 0.9m further
    # back, where the wall swallows it.
    ext = 0.9
    bx3 = (x0 + x1) / 2 - fx0 * (RW_D + ext) / 2
    by3 = (y0 + y1) / 2 - fy0 * (RW_D + ext) / 2
    sx3 = abs(dx) + ((RW_D + ext) if fx0 else 1.6)
    sy3 = abs(dy) + ((RW_D + ext) if fy0 else 1.6)
    box(max(sx3, RW_D), max(sy3, RW_D), 0.8, (bx3, by3, 2.5 + 7.4), stone)
    box(max(sx3, RW_D) + 0.6, max(sy3, RW_D) + 0.6, 0.9, (bx3, by3, 2.5 + 8.15), stone)

riwaq_run(-81, 24.5, 81, 24.5, (0, 1))
riwaq_run(-81, 99.5, 81, 99.5, (0, -1))
riwaq_run(-80.5, 25, -80.5, 99, (1, 0))
riwaq_run(80.5, 25, 80.5, 99, (-1, 0))

for sxg in (-1, 1):
    for syg in (-1, 1):
        bx2, by2 = sxg * 40, 62 + syg * 22
        box(46, 15, 1.0, (bx2, by2, 2.75), stone)
        box(43.5, 12.5, 0.9, (bx2, by2, 2.95), earth)
        col(bx2, by2, 0.6, 23, 7.5, 0.65)

# THE FOUNTAIN: water INSIDE its rims, calm, faintly lit
cyl(7.0, 1.4, (0, 62, 2.5 + 0.7), stone, verts=8, smooth=False)
cyl(6.0, 1.3, (0, 62, 2.5 + 0.75), water, verts=24)
cyl(1.1, 2.6, (0, 62, 2.5 + 1.8), stone, verts=10)
cyl(3.4, 0.9, (0, 62, 2.5 + 3.3), stone, verts=8, smooth=False)
cyl(2.7, 0.85, (0, 62, 2.5 + 3.42), water, verts=20)
cyl(0.5, 1.6, (0, 62, 2.5 + 4.4), stone, verts=10)
sphere(0.62, (0, 62, 2.5 + 5.4), gold, seg=14, rings=9)
col(0, 62, 1.9, 7.2, 7.2, 1.9)

# ======================================================== THE FIREFLIES
# points of light drifting near every dome and over the garden - pure light,
# no bodies, as the aniconism holds. Two colours: warm ember and pale violet.
for (ax_, ay_, az_, br_) in SPARK_ANCHORS:
    for i in range(5):
        a = random.uniform(0, 6.283)
        el = random.uniform(-0.15, 0.9)
        rr = br_ * random.uniform(1.35, 2.3)
        FLIES.append({"x": round(ax_ + math.cos(a) * math.cos(el) * rr, 2),
                      "z": round(-(ay_ + math.sin(a) * math.cos(el) * rr), 2),
                      "y": round(az_ + math.sin(el) * rr + random.uniform(0, br_ * 0.5), 2),
                      "c": 0 if random.random() < 0.62 else 1})
for i in range(46):
    FLIES.append({"x": round(random.uniform(-80, 80), 2),
                  "z": round(-random.uniform(26, 98), 2),
                  "y": round(random.uniform(3.6, 12.0), 2),
                  "c": 0 if random.random() < 0.55 else 1})

# ============================================================ MATERIALS
def make_mesh(pool, base, rough, metal, tex=None, tint=None, emis=None, estr=0.5, uvs=6.0):
    if not pool.v:
        return None
    me = bpy.data.meshes.new(pool.name)
    me.from_pydata(pool.v, [], pool.f)
    me.update()
    for i, p in enumerate(me.polygons):
        p.use_smooth = pool.smooth[i]
    if tex:
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            n = poly.normal
            ax_ = 2 if abs(n.z) >= max(abs(n.x), abs(n.y)) else (0 if abs(n.x) >= abs(n.y) else 1)
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                if ax_ == 0:
                    uv.data[li].uv = (co.y / uvs, co.z / uvs)
                elif ax_ == 1:
                    uv.data[li].uv = (co.x / uvs, co.z / uvs)
                else:
                    uv.data[li].uv = (co.x / uvs, co.y / uvs)
    ob = bpy.data.objects.new(pool.name, me)
    bpy.context.collection.objects.link(ob)
    m = bpy.data.materials.new(pool.name)
    m.use_nodes = True
    b2 = m.node_tree.nodes["Principled BSDF"]
    b2.inputs["Base Color"].default_value = base
    b2.inputs["Roughness"].default_value = rough
    b2.inputs["Metallic"].default_value = metal
    if emis:
        try:
            b2.inputs["Emission Color"].default_value = emis
        except KeyError:
            b2.inputs["Emission"].default_value = emis
        b2.inputs["Emission Strength"].default_value = estr
    if tex:
        path = os.path.abspath(os.path.join(ASSETS, tex))
        if os.path.exists(path):
            img = bpy.data.images.load(path)
            tn = m.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = img
            if tint:
                mix = m.node_tree.nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'
                mix.inputs['Fac'].default_value = 1.0; mix.inputs['Color2'].default_value = tint
                m.node_tree.links.new(tn.outputs['Color'], mix.inputs['Color1'])
                m.node_tree.links.new(mix.outputs['Color'], b2.inputs['Base Color'])
            else:
                m.node_tree.links.new(tn.outputs['Color'], b2.inputs['Base Color'])
            img.pack()
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


parts = []
parts.append(make_mesh(stone, (0.86, 0.82, 0.74, 1), 0.72, 0.0,
                       tex="t_ashlar_d.jpg", tint=(1.56, 1.47, 1.24, 1), uvs=6.0))
parts.append(make_mesh(gold, (1.0, 0.78, 0.28, 1), 0.20, 0.85,
                       emis=(0.62, 0.44, 0.13, 1), estr=0.75))
parts.append(make_mesh(wood, (0.52, 0.38, 0.24, 1), 0.85, 0.0,
                       tex="t_door_d.jpg", uvs=1.4))
# THE CARPETS. They were made of `wood`, which wears the DOOR sheet - panels,
# studs and arches - so every runner in the palace was a row of doors lying on
# the floor. They have their own surface now.
parts.append(make_mesh(rug, (0.72, 0.60, 0.52, 1), 0.95, 0.0,
                       tex="t_carpet_d.jpg", uvs=3.4))
parts.append(make_mesh(glow, (1.0, 0.76, 0.38, 1), 0.9, 0.0,
                       emis=(1.0, 0.62, 0.22, 1), estr=3.0))
parts.append(make_mesh(earth, (0.30, 0.22, 0.15, 1), 1.0, 0.0))
parts.append(make_mesh(water, (0.22, 0.34, 0.48, 1), 0.12, 0.0,
                       emis=(0.16, 0.26, 0.38, 1), estr=0.35))
# THE SAPPHIRE: deep blue-violet with a light pink breath, and the faint
# even inner glow of an ore block - luminous, never a lamp
# HIS BLENDING ORDER: the candy metal sat apart from the sandy stone and
# the night. The violet stays, but as WEATHERED stone-metal: desaturated
# toward the night sky, matte enough to hold moonlight instead of throwing
# it, the inner glow down to a breath. A dome that belongs to its place.
parts.append(make_mesh(sapph, (0.27, 0.21, 0.38, 1), 0.44, 0.70,
                       emis=(0.20, 0.15, 0.28, 1), estr=0.20))
parts.append(make_mesh(spark, (1.0, 0.9, 0.7, 1), 0.9, 0.0,
                       emis=(1.0, 0.82, 0.52, 1), estr=4.0))
parts.append(make_mesh(sparkv, (0.9, 0.7, 1.0, 1), 0.9, 0.0,
                       emis=(0.78, 0.48, 0.95, 1), estr=4.0))
parts = [p for p in parts if p]

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1:
    bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "qasr"

ob.scale = (QSCALE, QSCALE, QSCALE)
bpy.ops.object.transform_apply(scale=True)
for c in COLS:
    c["c"] = [round(v * QSCALE, 2) for v in c["c"]]
    c["h"] = [round(v * QSCALE, 2) for v in c["h"]]

me = ob.data
me.calc_loop_triangles()
print("RESULT qasr verts=%d tris=%d" % (len(me.vertices), len(me.loop_triangles)))
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)

with open(os.path.splitext(OUT)[0] + ".col.json", "w") as f:
    json.dump({"boxes": COLS}, f)
for dd in DOORS:
    for k in ("x", "z", "y0", "w", "h"):
        dd[k] = round(dd[k] * QSCALE, 2)
for ff in FLIES:
    for k in ("x", "y", "z"):
        ff[k] = round(ff[k] * QSCALE, 2)
with open(os.path.splitext(OUT)[0] + ".door.json", "w") as f:
    json.dump({"doors": DOORS}, f)
with open(os.path.splitext(OUT)[0] + ".fx.json", "w") as f:
    json.dump({"fireflies": FLIES}, f)
print("WROTE", OUT, "doors", len(DOORS), "flies", len(FLIES))
