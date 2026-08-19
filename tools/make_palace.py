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
FIRES = []      # braziers the engine lights: {x,y,z,s,p,g}
PLAN = []       # the layout map: every room and region, for naming
GARDEN = []     # what the engine plants in the court: {k,x,y,z,r,s}
LAMPS = []      # every lantern and sconce, so the engine puts real light in it
COVER = []      # the beds, as rectangles: the engine sows the cards itself

# One level for the whole compound: the hall floor, the court paving and every
# room floor are THIS number. They used to differ by 15-20 cm, which is a step
# down in every doorway and a dark line at every floor edge.
CY = 2.35


def region(code, kind, shape, cx, cy, a, b, note="", rot=0.0):
    """One named place on the plan. The map is drawn from THIS, not from a
    drawing made by hand, so it can never drift away from the palace."""
    PLAN.append({"code": code, "kind": kind, "shape": shape,
                 "x": round(cx, 2), "y": round(cy, 2),
                 "a": round(a, 2), "b": round(b, 2),
                 "rot": round(rot, 3), "note": note})


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
        # CLOTH CANNOT BE PROJECTED. Every other surface here takes its uv from
        # where it stands in the world, which is right for stone and wrong for
        # a carpet: a rug wants ONE whole carpet - border and all - laid on it,
        # not a slice of an endless sheet. A face may carry its own uvs here.
        self.uvq = {}          # face index -> [(u, v), ...]

    def quad(self, a, b, c, d, smooth=False, uv=None):
        self.f.append((a, b, c, d))
        self.smooth.append(smooth)
        if uv:
            self.uvq[len(self.f) - 1] = uv

    def tri(self, a, b, c, smooth=False):
        self.f.append((a, b, c))
        self.smooth.append(smooth)


stone = Pool("stone")
gold = Pool("gold")
wood = Pool("wood")
rug = Pool("rug")
cloth = Pool("cloth")      # the curtains
tile = Pool("tile")        # the zellij dado
flor = Pool("flor")        # the carved floral bands
pane = Pool("pane")        # the amber panes of the lanterns
folia = Pool("folia")      # the leaves of the garlands
bloom = Pool("bloom")      # their flowers
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


def annulus(cx, cy, z_top, th, ri, ro, pool, verts=44, smooth=True):
    """A flat ring of stone: a balcony floor, a coping, a collar."""
    b0 = len(pool.v)
    for zz in (z_top - th, z_top):
        for rr in (ri, ro):
            for i in range(verts):
                a = i / verts * 2 * math.pi
                pool.v.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr, zz))

    def V(l, w, i):
        return b0 + l * 2 * verts + w * verts + (i % verts)

    for i in range(verts):
        j = i + 1
        pool.quad(V(1, 0, i), V(1, 1, i), V(1, 1, j), V(1, 0, j))
        pool.quad(V(0, 0, j), V(0, 1, j), V(0, 1, i), V(0, 0, i))
        pool.quad(V(0, 1, i), V(0, 1, j), V(1, 1, j), V(1, 1, i), smooth)
        pool.quad(V(0, 0, j), V(0, 0, i), V(1, 0, i), V(1, 0, j), smooth)


def col_yaw(cx, cy, cz, sx, sy, sz, yaw):
    """Collision for a box that stands at an angle. A collision box cannot be
    turned on its own, so this writes its TRUE axis-aligned bound - not the fat
    square you get by using the long side for both axes, which is what closed
    the minaret's doorway with the collision of the rail beside it."""
    c2, s3 = abs(math.cos(yaw)), abs(math.sin(yaw))
    col(cx, cy, cz, sx / 2 * c2 + sy / 2 * s3, sx / 2 * s3 + sy / 2 * c2, sz / 2)


def col_annulus(cx, cy, zc, hz, ri, ro, dy=0.55, bias=0.14):
    """Collision for a ring. A collision box cannot be turned on its own, so
    the ring is cut into rows of axis-aligned boxes; each row leans OUTWARD by
    a hand's width at both edges, because standing on a finger of invisible
    floor is a nuisance and falling through a floor you can see is not."""
    n = max(1, int(math.ceil(2 * ro / dy)))
    step = 2 * ro / n
    for k in range(n):
        yc = -ro + step * (k + 0.5)
        oh = math.sqrt(max(0.0, ro * ro - yc * yc)) + bias
        ih = math.sqrt(max(0.0, ri * ri - yc * yc)) - bias
        if oh <= 0.06:
            continue
        if ih <= 0.06:
            col(cx, cy + yc, zc, oh, step / 2 + 0.04, hz)
        else:
            w = (oh - ih) / 2.0
            col(cx - (ih + w), cy + yc, zc, w, step / 2 + 0.04, hz)
            col(cx + (ih + w), cy + yc, zc, w, step / 2 + 0.04, hz)


# ------------------------------------------------------------------ the cloth
def carpet(cx, cy, z, w, l, yaw=0.0, th=0.085, unit=3.2):
    """A carpeted floor, laid with ITS OWN uvs. `unit` is how wide one whole
    carpet is - about four and a half metres, which is a large one - so a big
    floor gets a grid of carpets laid side by side and end to end, the way a
    hall is actually carpeted. Stretching one design over the whole floor put
    three metre flowers on it."""
    ru = max(1, int(round(w / unit)))
    rv = max(1, int(round(l / unit)))
    hx, hy = w / 2.0, l / 2.0
    c, s2 = math.cos(yaw), math.sin(yaw)

    def P(x, y, zz):
        return (cx + x * c - y * s2, cy + x * s2 + y * c, zz)

    b0 = len(rug.v)
    for zz in (z, z + th):
        for (x, y) in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)):
            rug.v.append(P(x, y, zz))
    rug.quad(b0 + 0, b0 + 3, b0 + 2, b0 + 1)
    for k in range(4):
        k2 = (k + 1) % 4
        rug.quad(b0 + k, b0 + k2, b0 + 4 + k2, b0 + 4 + k)
    rug.quad(b0 + 4, b0 + 5, b0 + 6, b0 + 7,
             uv=[(0.0, 0.0), (ru, 0.0), (ru, rv), (0.0, rv)])


def curtain(cx, cy, z_top, w, h, face=(0, -1), sides=(-1, 1), rod=True):
    """Cloth hung in an opening and GRASPED TO THE SIDE, held by a golden
    holder - his order. A panel falls from the rod, is pinched at the holder a
    little above half height, and flares again to the floor. That pinch is the
    whole thing: without it a curtain is a board leaning on a wall."""
    fl = math.hypot(face[0], face[1]) or 1.0
    fx, fy = face[0] / fl, face[1] / fl
    yaw = math.atan2(fy, fx) + math.pi / 2
    cs, sn = math.cos(yaw), math.sin(yaw)

    def P(a, o, z):
        return (cx + a * cs - o * sn, cy + a * sn + o * cs, z)

    TT = 0.50                       # where along the drop the holder grips
    NT, NU, TH = 9, 5, 0.035
    for sd in sides:
        def edges(t):
            """the panel's two edges as they run down: bunched, pinched, flared"""
            if t <= TT:
                f = t / TT
                f = f * f * (3 - 2 * f)
                a0 = 0.20 + (w / 2 - 0.25) * f
                a1 = (w / 2 + 0.55) + 0.20 * f
            else:
                f = (t - TT) / (1 - TT)
                f = f * f * (3 - 2 * f)
                a0 = (w / 2 - 0.25) - 0.62 * f
                a1 = (w / 2 + 0.75) + 0.34 * f
            return sd * a0, sd * a1

        def amp(t):
            return 0.05 + 0.30 * (t ** 1.2) * \
                (1.0 - 0.55 * math.exp(-((t - TT) ** 2) / 0.012))

        grid = []
        for it in range(NT + 1):
            t = it / float(NT)
            a0, a1 = edges(t)
            row = []
            for iu in range(NU + 1):
                u = iu / float(NU)
                a = a0 + (a1 - a0) * u
                # the two panels hang at slightly different depths, as two
                # curtains on one rod do - level with each other they meet in
                # the middle and fight for every pixel
                o = 0.16 + (0.05 if sd > 0 else 0.0) + \
                    amp(t) * math.sin(u * math.pi * 3.0)
                row.append((a, o, z_top - h * t))
            grid.append(row)
        b0 = len(cloth.v)
        for side in (0, 1):
            for row in grid:
                for (a, o, z) in row:
                    cloth.v.append(P(a, o - side * TH, z))
        VP = (NT + 1) * (NU + 1)

        def V(side, it, iu):
            return b0 + side * VP + it * (NU + 1) + iu

        for it in range(NT):
            vt0 = it / float(NT) * (h / 2.1)
            vt1 = (it + 1) / float(NT) * (h / 2.1)
            for iu in range(NU):
                u0, u1 = iu / float(NU), (iu + 1) / float(NU)
                cloth.quad(V(0, it, iu), V(0, it, iu + 1), V(0, it + 1, iu + 1),
                           V(0, it + 1, iu), smooth=True,
                           uv=[(u0, vt0), (u1, vt0), (u1, vt1), (u0, vt1)])
                cloth.quad(V(1, it + 1, iu), V(1, it + 1, iu + 1), V(1, it, iu + 1),
                           V(1, it, iu), smooth=True,
                           uv=[(u0, vt1), (u1, vt1), (u1, vt0), (u0, vt0)])
            for iu in (0, NU):      # the selvages: cloth has an edge, not a cut
                cloth.quad(V(0, it, iu), V(1, it, iu), V(1, it + 1, iu),
                           V(0, it + 1, iu), smooth=True)
        for iu in range(NU):                              # the hem
            cloth.quad(V(0, NT, iu), V(0, NT, iu + 1), V(1, NT, iu + 1),
                       V(1, NT, iu), smooth=True)

        # THE GOLDEN HOLDER: a cuff round the gathered cloth, on a short stem
        # out of the jamb, with a knob at its end.
        a0, a1 = edges(TT)
        am = (a0 + a1) / 2
        hz = z_top - h * TT
        hx_, hy_, _ = P(am, 0.16, hz)
        box(abs(a1 - a0) + 0.16, 0.34, 0.26, (hx_, hy_, hz), gold, yaw=yaw)
        jx, jy, _ = P(sd * (w / 2 + 0.62), 0.10, hz)
        box(0.44, 0.13, 0.13, (jx, jy, hz), gold, yaw=yaw)
        sphere(0.15, (jx, jy, hz), gold, seg=8, rings=6)
    if rod:
        rx, ry, _ = P(0, 0.16, z_top + 0.14)
        box(w + 1.9, 0.16, 0.16, (rx, ry, z_top + 0.14), gold, yaw=yaw)
        for sd2 in (-1, 1):
            ex, ey, _ = P(sd2 * (w / 2 + 0.95), 0.16, z_top + 0.14)
            sphere(0.17, (ex, ey, z_top + 0.14), gold, seg=8, rings=6)


# --------------------------------------------------------- the floral rope
def leaf3(cx, cy, cz, dv, sv, ln, wd):
    """One leaf: four points, two triangles, seen from both sides."""
    b0 = len(folia.v)
    folia.v.append((cx, cy, cz))
    folia.v.append((cx + dv[0] * ln * 0.42 + sv[0] * wd,
                    cy + dv[1] * ln * 0.42 + sv[1] * wd,
                    cz + dv[2] * ln * 0.42 + sv[2] * wd))
    folia.v.append((cx + dv[0] * ln, cy + dv[1] * ln, cz + dv[2] * ln))
    folia.v.append((cx + dv[0] * ln * 0.42 - sv[0] * wd,
                    cy + dv[1] * ln * 0.42 - sv[1] * wd,
                    cz + dv[2] * ln * 0.42 - sv[2] * wd))
    folia.quad(b0, b0 + 1, b0 + 2, b0 + 3)
    folia.quad(b0, b0 + 3, b0 + 2, b0 + 1)


def blossom3(cx, cy, cz, nrm, r, petal=None, eye=None, npet=5):
    """A five petal flower, flat, facing nrm - with a gold eye."""
    nx, ny, nz = nrm
    nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    nx, ny, nz = nx / nl, ny / nl, nz / nl
    ux, uy, uz = (-ny, nx, 0.0) if abs(nz) < 0.9 else (1.0, 0.0, 0.0)
    ul = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
    ux, uy, uz = ux / ul, uy / ul, uz / ul
    vx = ny * uz - nz * uy
    vy = nz * ux - nx * uz
    vz = nx * uy - ny * ux
    for (pool, rr, n) in (((petal or bloom), r, npet), ((eye or gold), r * 0.30, 3)):
        b0 = len(pool.v)
        pool.v.append((cx + nx * 0.012, cy + ny * 0.012, cz + nz * 0.012))
        for k in range(n):
            a0 = k * 2 * math.pi / n
            am = a0 + math.pi / n
            a1 = a0 + 2 * math.pi / n
            for (aa, q) in ((a0, 0.34), (am, 1.0), (a1, 0.34)):
                pool.v.append((cx + (math.cos(aa) * ux + math.sin(aa) * vx) * rr * q,
                               cy + (math.cos(aa) * uy + math.sin(aa) * vy) * rr * q,
                               cz + (math.cos(aa) * uz + math.sin(aa) * vz) * rr * q))
        for k in range(n):
            i0 = b0 + 1 + k * 3
            pool.tri(b0, i0, i0 + 1)
            pool.tri(b0, i0 + 1, i0 + 2)
            if pool is not gold:          # the eye lies on the petals: one side
                pool.tri(b0, i0 + 1, i0)
                pool.tri(b0, i0 + 2, i0 + 1)


def garland(p0, p1, sag, nrm=(0, 0, 1), seed=0, n=11):
    """A rope of leaves and flowers slung between two points and hanging in a
    half circle - his 'floral rope-like thing that stretches along it all the
    way, and goes in half circles'. It is what turns a bare arcade into a
    garden, and it costs almost nothing to carry."""
    rnd = random.Random(seed * 7919 + 13)
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        pts.append((p0[0] + (p1[0] - p0[0]) * t,
                    p0[1] + (p1[1] - p0[1]) * t,
                    p0[2] + (p1[2] - p0[2]) * t - sag * math.sin(math.pi * t)))
    for i in range(n):
        (x0, y0, z0), (x1, y1, z1) = pts[i], pts[i + 1]
        mx, my, mz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1e-6
        box(ln * 1.16, 0.20, 0.20, (mx, my, mz), folia,
            yaw=math.atan2(dy, dx),
            tilt=-math.asin(max(-1.0, min(1.0, dz / ln))))
        dv = (dx / ln, dy / ln, dz / ln)
        sv = (-dv[1], dv[0], 0.0)
        sl = math.hypot(sv[0], sv[1]) or 1.0
        sv = (sv[0] / sl, sv[1] / sl, 0.0)
        for k in (-1, 1):
            a = rnd.uniform(0.7, 1.5) * k
            ld = (dv[0] * math.cos(a) + sv[0] * math.sin(a) * 0.7,
                  dv[1] * math.cos(a) + sv[1] * math.sin(a) * 0.7,
                  -abs(math.sin(a)) * 0.55)
            leaf3(mx, my, mz, ld, sv, rnd.uniform(0.44, 0.68), rnd.uniform(0.16, 0.26))
        # HIS ORDER: more flowers in the hanging rope. One at every link,
        # and a second turned aside on most of them.
        blossom3(mx, my, mz - 0.13, nrm, rnd.uniform(0.20, 0.30))
        if i % 3 != 2:
            blossom3(mx + sv[0] * 0.20, my + sv[1] * 0.20, mz - 0.05,
                     (nrm[0] * 0.7 + sv[0] * 0.7, nrm[1] * 0.7 + sv[1] * 0.7, 0.25),
                     rnd.uniform(0.15, 0.24))



def swag_row(x0, y0, x1, y1, z, n, sag, nrm=(0, 0, 1), seed=0):
    """A run of garlands, each a half circle, hung end to end along a wall."""
    for i in range(n):
        t0, t1 = i / float(n), (i + 1) / float(n)
        garland((x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, z),
                (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1, z),
                sag, nrm=nrm, seed=seed * 131 + i)


def plant(k, x, y, z, rot=None, sc=1.0, col=None):
    """Something the ENGINE grows in the garden. The palace is one welded mesh
    and a tree is not: trees, flowers and grass are real models, so they are
    recorded here by name and place and the game plants them."""
    e = {"k": k, "x": round(x, 2), "z": round(-y, 2), "y": round(z, 2),
         "r": round(rot if rot is not None else random.uniform(0, 6.283), 3),
         "s": round(sc, 3)}
    if col:
        e["c"] = col
    GARDEN.append(e)


def torchpost(x, y, z):
    plant("p_torchpost", x, y, z)
    FIRES.append({"x": round(x, 2), "z": round(-y, 2), "y": round(z + 2.62, 2),
                  "s": 0.50, "p": 1.45, "g": round(z, 2)})


def lamp_at(cx, cy, cz, power=0.55, reach=8.0):
    LAMPS.append({"x": round(cx, 2), "z": round(-cy, 2), "y": round(cz, 2),
                  "p": power, "r": reach})


def lantern(cx, cy, z_top, drop=2.2, r=0.36, chain=True, power=0.55, reach=8.0):
    """A REAL lantern. The old one was a white box: an emissive block at
    strength three clips to white and stops being firelight altogether. This
    is a gold frame with amber panes and a candle burning inside it, and it
    tells the engine to put a real light where the flame is."""
    zc = z_top - drop
    if chain:
        cyl(0.045, drop - r * 1.5, (cx, cy, z_top - (drop - r * 1.5) / 2), gold, verts=6)
        cyl(0.10, 0.10, (cx, cy, z_top - 0.05), gold, verts=8)
    box(r * 2.45, r * 2.45, 0.10, (cx, cy, zc + r * 1.25), gold)      # the cap
    box(r * 2.15, r * 2.15, 0.10, (cx, cy, zc - r * 1.25), gold)      # the base
    for (dx, dy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        box(0.075, 0.075, r * 2.5, (cx + dx * r, cy + dy * r, zc), gold)
    for (dx, dy, sx2, sy2) in ((0, -1, r * 1.9, 0.05), (0, 1, r * 1.9, 0.05),
                               (-1, 0, 0.05, r * 1.9), (1, 0, 0.05, r * 1.9)):
        box(sx2, sy2, r * 2.2, (cx + dx * r, cy + dy * r, zc), pane)
    cyl(0.085, r * 0.95, (cx, cy, zc - r * 0.62), pane, verts=8)       # the wax
    cyl(0.052, 0.30, (cx, cy, zc + r * 0.02), glow, verts=6, r_top=0.006)
    sphere(0.085, (cx, cy, zc + r * 1.45), gold, seg=8, rings=6)
    lamp_at(cx, cy, zc, power, reach)


def sconce(cx, cy, cz, face, power=0.5, reach=7.0):
    """A light fixed to a wall or a pillar - an iron arm, a bowl, a flame in
    it. His rule: the light in a room comes FROM something you can see."""
    fl = math.hypot(face[0], face[1]) or 1.0
    fx, fy = face[0] / fl, face[1] / fl
    yaw = math.atan2(fy, fx)
    box(0.30, 0.16, 0.62, (cx, cy, cz), gold, yaw=yaw)                # back plate
    box(0.52, 0.09, 0.09, (cx + fx * 0.30, cy + fy * 0.30, cz + 0.10), gold,
        yaw=yaw, tilt=-0.42)
    ox, oy = cx + fx * 0.56, cy + fy * 0.56
    cyl(0.13, 0.20, (ox, oy, cz + 0.30), gold, verts=10, r_top=0.24)  # the bowl
    cyl(0.20, 0.06, (ox, oy, cz + 0.42), glow, verts=10)              # the coals
    cyl(0.135, 0.56, (ox, oy, cz + 0.72), glow, verts=6, r_top=0.008)
    lamp_at(ox, oy, cz + 0.52, power, reach)


def rose_boss(cx, cy, cz, nrm, r):
    """A carved rosette for a spandrel: a stone patera standing proud of the
    wall, a panel of carved leaf on it, a gilt flower on that. The first try
    was a flat pink star laid on the stone and it read as a sticker."""
    nl = math.hypot(nrm[0], nrm[1]) or 1.0
    ux, uy = nrm[0] / nl, nrm[1] / nl
    yaw = math.atan2(uy, ux) + math.pi / 2
    box(r * 2.6, 0.22, r * 2.6, (cx + ux * 0.03, cy + uy * 0.03, cz), stone, yaw=yaw)
    box(r * 2.1, 0.30, r * 2.1, (cx + ux * 0.13, cy + uy * 0.13, cz), flor, yaw=yaw)
    for (sa, sz2) in ((1, r * 2.1), (-1, r * 2.1)):        # a gold frame round it
        box(r * 2.3, 0.16, 0.16, (cx + ux * 0.22, cy + uy * 0.22, cz + sa * r * 1.07),
            gold, yaw=yaw)
        box(0.16, 0.16, r * 2.3,
            (cx + ux * 0.22 - math.sin(yaw) * 0 + math.cos(yaw) * sa * r * 1.07,
             cy + uy * 0.22 + math.sin(yaw) * sa * r * 1.07, cz), gold, yaw=yaw)
    blossom3(cx + ux * 0.30, cy + uy * 0.30, cz, (ux, uy, 0.0), r * 0.86,
             petal=gold, eye=bloom, npet=8)


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


def arch(cx, cy, z0, w, h, depth, pool, frame=0.55, face=(0, -1), lit=True,
         head_only=False):
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
    if not head_only:
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
    # The surround was 45 cm thick and stood a third of the reveal proud of
    # the wall, so from outside every window read as a wooden BOARD nailed on.
    # It is a slim frame set INTO the reveal now: it reads as joinery in an
    # opening, which is what it is.
    lx, ly = 0, depth * 0.06
    box(w + 0.55, 0.16, h + 0.5, (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs,
        z0 + (h + 0.5) / 2 - 0.16), wood, yaw=yaw)
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


def minaret(cx, cy, htot, code=""):
    if code:
        region(code, "minaret", "circle", cx, cy, 3.1 * 1.75 * 2, 3.1 * 1.75 * 2,
               "spiral stair round an open well to a walking gallery and a brazier")
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

    # ------------------------------------------------ THE STAIR AND ITS WAY OUT
    # It used to climb into a solid stone plug - two full discs stacked on one
    # another, neither with a hole in it - so a man who climbed a hundred and
    # sixty steps met a ceiling. The flight now rises to one riser under the
    # gallery floor and steps out through a real opening cut in it.
    GR = r * 1.75                 # how far the gallery stands out from the shaft
    GIN = 2.30                    # the well mouth, where the treads end
    FTH = 0.45                    # the gallery floor slab
    cyl(0.55, lz - 0.4, (cx, cy, 0.4 + (lz - 0.4) / 2), stone, verts=12)
    top_z = lz - 0.11             # the last tread's face is the gallery floor
    n_steps = max(6, int(round((top_z - 0.73) / 0.30)) + 1)
    rise = (top_z - 0.73) / (n_steps - 1)
    ph = math.pi / 2 - (n_steps - 1) * 0.42     # the last tread faces the opening
    for i in range(n_steps):
        a = ph + i * 0.42
        last = i >= n_steps - 4
        tl = 2.60 if last else 1.70             # the last treads reach the ring
        tr = 1.75 if last else 1.45
        sx_ = cx + math.cos(a) * tr
        sy_ = cy + math.sin(a) * tr
        sz2 = 0.73 + i * rise
        box(tl, 0.74, 0.22, (sx_, sy_, sz2), stone, yaw=a + math.pi / 2)
        col(sx_, sy_, sz2, tl / 2 + 0.05, tl / 2 + 0.05, 0.12)
    nlamp = max(2, int((lz - 8.0) / 9.0))       # or the climb is a black pipe
    for i in range(nlamp):
        a = ph + i * 2.7
        lz2 = 5.0 + (lz - 9.0) * i / float(nlamp)
        lx2 = cx + math.cos(a) * (r - 0.44)
        ly2 = cy + math.sin(a) * (r - 0.44)
        sconce(lx2, ly2, lz2, (-math.cos(a), -math.sin(a)), power=0.5, reach=7.5)

    # ------------------------------------------------------------ THE GALLERY
    # A place to stand: a ring wide enough to walk round, a parapet you cannot
    # fall through, and the roof carried on columns at the rim so the middle of
    # the floor stays clear.
    cyl(r * 1.06, 1.20, (cx, cy, lz - FTH - 0.60), stone, verts=32, r_top=GR + 0.12)
    annulus(cx, cy, lz - FTH, 0.24, r * 0.92, GR + 0.26, stone, verts=40)
    annulus(cx, cy, lz, FTH, GIN, GR, stone, verts=40)
    col_annulus(cx, cy, lz - FTH / 2, FTH / 2, GIN, GR, dy=0.62)
    # THE WELL STAYS OPEN, and this is not laziness - it is the only thing that
    # works. A spiral rising 30 cm every 24 degrees needs two and a half metres
    # of clear air over every tread; roof the well and the man three steps down
    # has his head in the slab. So the well is left open and RAILED, with one
    # gap where the top tread comes out, and the light of the stair is seen
    # from the gallery all the way down.
    RSEG = 20
    for k in range(RSEG):
        ra = (k + 0.5) / RSEG * 2 * math.pi
        if abs(((ra - math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) < 0.52:
            continue                            # the way out
        sw = 2 * math.pi * 2.48 / RSEG * 1.25
        rx3 = cx + math.cos(ra) * 2.48
        ry3 = cy + math.sin(ra) * 2.48
        box(sw, 0.36, 1.05, (rx3, ry3, lz + 0.525), stone, yaw=ra + math.pi / 2)
        box(sw + 0.10, 0.48, 0.14, (rx3, ry3, lz + 1.12), stone, yaw=ra + math.pi / 2)
        box(sw, 0.40, 0.09, (rx3, ry3, lz + 0.72), gold, yaw=ra + math.pi / 2)
        col_yaw(rx3, ry3, lz + 0.55, sw + 0.10, 0.44, 1.10, ra + math.pi / 2)
    PW = 1.05                                   # the parapet
    annulus(cx, cy, lz + PW, PW, GR - 0.38, GR, stone, verts=40)
    annulus(cx, cy, lz + PW + 0.18, 0.18, GR - 0.52, GR + 0.14, stone, verts=40)
    annulus(cx, cy, lz + PW * 0.66, 0.10, GR - 0.40, GR + 0.03, gold, verts=40)
    col_annulus(cx, cy, lz + PW / 2, PW / 2, GR - 0.42, GR + 0.04, dy=0.70)
    for i in range(24):
        a = i / 24.0 * 2 * math.pi
        box(0.44, 0.40, 0.34, (cx + math.cos(a) * (GR - 0.20),
                               cy + math.sin(a) * (GR - 0.20),
                               lz + PW + 0.36 + 0.17), stone, yaw=a)
    CAP = 4.60
    PCR = GR - 0.30                             # the columns ride ON the parapet
    for i in range(8):
        a = i / 8.0 * 2 * math.pi + math.pi / 8
        px = cx + math.cos(a) * PCR
        py = cy + math.sin(a) * PCR
        cyl(0.44, 0.34, (px, py, lz + 0.17), stone, verts=10)
        cyl(0.29, CAP - 0.68, (px, py, lz + 0.34 + (CAP - 0.68) / 2), stone, verts=10)
        cyl(0.44, 0.34, (px, py, lz + CAP - 0.17), stone, verts=10)
        col(px, py, lz + CAP / 2, 0.36, 0.36, CAP / 2)
    for i in range(8):                          # the arcade between the columns
        a = i / 8.0 * 2 * math.pi + math.pi / 4
        fx2, fy2 = math.cos(a), math.sin(a)
        ch = 2 * PCR * math.sin(math.pi / 8) + 0.5
        arch(cx + fx2 * PCR, cy + fy2 * PCR, lz + PW + 0.75, ch, CAP - PW - 0.75,
             0.46, stone, frame=0.30, lit=None, face=(fx2, fy2), head_only=True)
    annulus(cx, cy, lz + CAP + 0.46, 0.46, GR - 1.15, GR + 0.12, stone, verts=40)
    cyl(GR + 0.16, 0.55, (cx, cy, lz + CAP + 0.735), stone, verts=32)
    dome(cx, cy, lz + CAP + 1.01, r * 1.0, r * 2.1, ribs=12, drum=False)

    # THE BRAZIER. His order: the light up here is a fire, and it is seen from
    # far. A bowl of burning coals in the middle of the floor - the glow is
    # baked into the model so it carries even when the flame drops to one
    # tongue at distance, and the engine lights a real fire on top of it.
    bz0 = lz
    cyl(0.62, 1.10, (cx, cy, bz0 + 0.55), stone, verts=12)     # the newel, carried up
    cyl(0.86, 0.22, (cx, cy, bz0 + 1.21), stone, verts=14)
    cyl(0.66, 0.66, (cx, cy, bz0 + 1.63), stone, verts=18, r_top=1.16)
    annulus(cx, cy, bz0 + 2.02, 0.17, 0.98, 1.26, gold, verts=20)
    cyl(0.96, 0.26, (cx, cy, bz0 + 1.88), glow, verts=18)
    col(cx, cy, bz0 + 1.05, 0.90, 0.90, 1.05)
    FIRES.append({"x": round(cx, 2), "z": round(-cy, 2), "y": round(bz0 + 2.04, 2),
                  "s": 1.5, "p": 2.6, "g": round(bz0 + 1.30, 2)})


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
    lantern(0, lyc, z1 + S1_H - 1.5, drop=3.4, r=0.30, power=0.95, reach=15.0)
# SCONCES ON THE PILLARS. A hall lit from nowhere is what made the inside read
# as a photograph of stone; every light in here now hangs on something.
for sxc in (-1, 1):
    for cyc in (-10.5, -3.5, 3.5, 10.5):
        for fsx in (-1, 1):
            sconce(sxc * 8.5 + fsx * 1.02, cyc, CY + 2.35, (fsx, 0),
                   power=0.55, reach=11.0)
# ORNAMENT ON THE HALL WALLS. Bare coursed stone from floor to cornice is
# what made the inside read as a store room. Three courses do the work an
# Andalusi hall does: a plinth-high dado of dark stone, a string course over
# it, and a blind arcade of pointed arches standing on the dado all the way
# round - the same arches as the facade, only shallow.
# A DADO OF TILE. It was painted in the DOME's violet - one flat stripe that
# said nothing at eye level. It is zellij now, waist high, with a gold course
# over it and a carved floral band over that; then the blind arcade stands on
# the band, cut deep enough to throw a shadow, each bay carrying a field of
# carved leaf and a rosette in every spandrel.
DADO = CY + 1.85
for _sy in (17 - WT, -(17 - WT)):
    _s = 1 if _sy > 0 else -1
    box(44.6, 0.30, 1.85, (0, _sy - 0.15 * _s, CY + 0.925), tile)
    box(44.6, 0.40, 0.24, (0, _sy - 0.20 * _s, DADO + 0.12), gold)
    box(44.6, 0.30, 0.90, (0, _sy - 0.15 * _s, DADO + 0.69), flor)
    box(44.6, 0.40, 0.20, (0, _sy - 0.20 * _s, DADO + 1.24), gold)
for _sx in (23 - WT, -(23 - WT)):
    _s = 1 if _sx > 0 else -1
    box(0.30, 32.6, 1.85, (_sx - 0.15 * _s, 0, CY + 0.925), tile)
    box(0.40, 32.6, 0.24, (_sx - 0.20 * _s, 0, DADO + 0.12), gold)
    box(0.30, 32.6, 0.90, (_sx - 0.15 * _s, 0, DADO + 0.69), flor)
    box(0.40, 32.6, 0.20, (_sx - 0.20 * _s, 0, DADO + 1.24), gold)
ARC_Z = DADO + 1.40
for _i in range(7):
    _x = -19.2 + 38.4 * _i / 6.0
    for _sy2 in (1, -1):
        _yw = _sy2 * (17 - WT - 0.05)
        arch(_x, _yw, ARC_Z, 3.6, 3.40, 0.86, stone,
             frame=0.40, lit=None, face=(0, -_sy2))
        box(2.9, 0.14, 3.0, (_x, _yw - _sy2 * 0.06, ARC_Z + 1.62), flor)
        if _i < 6:
            rose_boss(_x + 3.2, _sy2 * (17 - WT), ARC_Z + 2.90, (0, -_sy2, 0), 0.40)
for _j in range(5):
    _y = -12.8 + 25.6 * _j / 4.0
    for _sx2 in (1, -1):
        _xw = _sx2 * (23 - WT - 0.05)
        arch(_xw, _y, ARC_Z, 3.6, 3.40, 0.86, stone,
             frame=0.40, lit=None, face=(-_sx2, 0))
        box(0.14, 2.9, 3.0, (_xw - _sx2 * 0.06, _y, ARC_Z + 1.62), flor)
        if _j < 4:
            rose_boss(_sx2 * (23 - WT), _y + 3.2, ARC_Z + 2.90, (-_sx2, 0, 0), 0.40)
# THE GARLANDS, hung in half circles under the ceiling all the way round
for _sy3 in (1, -1):
    swag_row(-20.4, _sy3 * (17 - WT - 0.55), 20.4, _sy3 * (17 - WT - 0.55),
             z1 + S1_H - 1.15, 7, 0.78, nrm=(0, -_sy3, 0), seed=11 + _sy3)
for _sx3 in (1, -1):
    swag_row(_sx3 * (23 - WT - 0.55), -14.6, _sx3 * (23 - WT - 0.55), 14.6,
             z1 + S1_H - 1.15, 5, 0.78, nrm=(-_sx3, 0, 0), seed=31 + _sx3)
# and between the two rows of columns, so the middle of the hall is dressed too
for _sxg in (-1, 1):
    swag_row(_sxg * 8.5, -10.5, _sxg * 8.5, 10.5, z1 + S1_H - 1.55, 3, 0.72,
             nrm=(-_sxg, 0, 0), seed=51 + _sxg)

# CLOTH AT EVERY WINDOW, not at one door. The hall's ground storey has
# nineteen openings in its outer walls; each one gets its curtain, hung inside.
for _wx in (-19, -15, -11, 11, 15, 19):
    curtain(_wx, -(17 - WT) + 0.10, CY + 5.40, 2.6, 5.40, face=(0, -1))
    curtain(_wx * 0.72, (17 - WT) - 0.10, CY + 5.40, 2.6, 5.40, face=(0, 1))
for _sxw2 in (-1, 1):
    for _i2 in range(4):
        _cy2 = -12 + 24 * (_i2 + 0.5) / 4
        curtain(_sxw2 * ((23 - WT) - 0.10), _cy2, CY + 5.40, 2.6, 5.40,
                face=(_sxw2, 0))

# THE CARPETS: a runner down the middle and one in each side aisle
carpet(0, -1, CY, 7.0, 26)
for _sxr in (-1, 1):
    carpet(_sxr * 15.4, 0, CY, 9.6, 24)
# and the cloth at the two great doors, grasped to the side by a gold holder
curtain(0, 15.22, CY + 8.30, 5.4, 8.30, face=(0, 1))
curtain(0, -18.70, CY + 6.60, 5.0, 6.60, face=(0, -1))
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
box(9.4, 3.9, CY, (0, -18.95, CY / 2), stone)
col(0, -18.95, CY / 2, 4.7, 1.95, CY / 2)
# the grand stair: the hall floor stood 2.35 m above the approach with
# nothing to climb - eight solid treads from the ground to the gate
NST = 10
for i_st in range(NST):
    st_h = CY - CY * (i_st + 1) / (NST + 1.0)
    st_y = -20.9 - 0.66 * (i_st + 1)
    box(10.6, 0.70, st_h, (0, st_y, st_h / 2), stone)
    col(0, st_y, st_h / 2, 5.3, 0.35, st_h / 2)
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

region("H", "hall", "rect", 0, 0, (23 - WT) * 2, (17 - WT) * 2,
       "the great hall: eight columns, tiled dado, blind arcade, garlands, "
       "three ranks of carpet")
region("P", "porch", "rect", 0, -19.0, 15.0, 6.0,
       "the iwan landing, inside the great portal")
region("X", "stair", "rect", 0, -24.5, 10.6, 7.0,
       "ten shallow treads from the ground to the hall floor")
for _lv, (_nm, _z, _h) in enumerate((("L2", z2, S2_H), ("L3", z3, S3_H),
                                     ("L4", z4, S4_H), ("L5", z5, S5_H),
                                     ("L6", z6, S6_H), ("L7", z7, 21.0))):
    region(_nm, "level", "none", 0, 0, 0, 0,
           "storey %d of the centre block, floor at %.1f m" % (_lv + 2, _z * QSCALE))


# ============================================================ THE COMPOUND
def module(cx, cy, face, gate=False, code=""):
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
    fl_z = CY                                   # ONE level for the whole compound
    ceil_z = W1 - 0.9                           # room ceiling underside
    sx_, sy_ = sized(w_hx * 2 + 1.4, w_hy * 2 + 1.4)
    box(sx_, sy_, 1.6, (cx, cy, 0.8), stone)                       # plinth
    col(cx, cy, 0.8, sx_ / 2, sy_ / 2, 0.8)
    fx_, fy_ = sized(w_hx * 2, w_hy * 2)
    box(fx_, fy_, 0.5, (cx, cy, CY - 0.25), stone)                 # room floor
    col(cx, cy, CY - 0.25, fx_ / 2, fy_ / 2, 0.25)
    # AN APRON AT THE DOOR. The court paving stopped short of the modules, so
    # walking out of a room was a step into a hole four metres wide. Every door
    # now has its own solid ground, whatever the court does.
    apx, apy = P(0, -(w_hy + 4.0))
    apsx, apsy = sized(w_hx * 2 - 1.0, 9.0)
    box(apsx, apsy, CY, (apx, apy, CY / 2), stone)
    col(apx, apy, CY / 2, apsx / 2, apsy / 2, CY / 2)
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
        # the room dressed: a carpet, a curtain at the door, hanging lanterns
        rx_, ry_ = P(0, 0)
        carpet(rx_, ry_, fl_z, 7.2, w_hy * 1.5, yaw=math.atan2(-ox, oy))
        cux, cuy = P(0, -(w_hy - WT2 / 2 - 1.0))
        curtain(cux, cuy, fl_z + 5.0, 3.0, 5.0, face=inward)
        for ll in (-4.5, 4.5):
            llx, lly = P(ll, 0)
            lantern(llx, lly, ceil_z - 0.1, drop=2.1, r=0.26,
                    power=0.62, reach=9.5)
        # and sconces on the side walls, two a side, so the room is lit by
        # things that are in it
        for sa3 in (-1, 1):
            for oo3 in (-5.5, 5.5):
                scx, scy = P(sa3 * (w_hx - WT2 - 0.20), oo3)
                sconce(scx, scy, fl_z + 2.30, (-sa3 * ax, -sa3 * ay),
                       power=0.5, reach=8.0)
        # and two flanking the door, so the way in is lit from inside
        for sa4 in (-1, 1):
            sdx, sdy = P(sa4 * 3.6, -(w_hy - WT2 - 0.18))
            sconce(sdx, sdy, fl_z + 2.30, inward, power=0.5, reach=8.0)
        # a second curtain, at the middle niche of the far wall
        nqx, nqy = P(0, w_hy - WT2 - 0.14)
        curtain(nqx, nqy, fl_z + 5.05, 1.9, 4.2, face=(ox, oy))
        # THE ROOM'S OWN COURSES: the same tiled dado, gold string and carved
        # floral band the great hall wears, on its three solid walls. A room
        # with a carpet and bare walls above it reads as a store with a rug in
        # it, which is what these were.
        for sa2 in (-1, 1):
            wx2, wy2 = P(sa2 * (w_hx - WT2 - 0.16), 0)
            tsx, tsy = sized(0.32, (w_hy - WT2) * 2)
            gsx, gsy = sized(0.42, (w_hy - WT2) * 2)
            box(tsx, tsy, 1.55, (wx2, wy2, fl_z + 0.775), tile)
            box(gsx, gsy, 0.20, (wx2, wy2, fl_z + 1.65), gold)
            box(tsx, tsy, 0.72, (wx2, wy2, fl_z + 2.11), flor)
            box(gsx, gsy, 0.18, (wx2, wy2, fl_z + 2.56), gold)
        wx2, wy2 = P(0, w_hy - WT2 - 0.16)
        tsx, tsy = sized((w_hx - WT2) * 2, 0.32)
        gsx, gsy = sized((w_hx - WT2) * 2, 0.42)
        box(tsx, tsy, 1.55, (wx2, wy2, fl_z + 0.775), tile)
        box(gsx, gsy, 0.20, (wx2, wy2, fl_z + 1.65), gold)
        box(tsx, tsy, 0.72, (wx2, wy2, fl_z + 2.11), flor)
        box(gsx, gsy, 0.18, (wx2, wy2, fl_z + 2.56), gold)
        for nn in (-8, 0, 8):
            nx_, ny_ = P(nn, w_hy - WT2 - 0.02)
            arch(nx_, ny_, fl_z + 2.85, 1.7, 3.1, 0.6, stone, frame=0.3,
                 lit=(nn == 0), face=inward)
            rose_boss(nx_ + inward[0] * 0.34, ny_ + inward[1] * 0.34,
                      fl_z + 2.20, (inward[0], inward[1], 0), 0.34)
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
    # HIS ORDER - the court arches carry a floral rope, hung in half circles
    # all along, and a carved band of leaf runs over them.
    fbx, fby = P(0, -(w_hy + 0.30))
    fbsx, fbsy = sized(w_hx * 2 - 1.2, 0.36)
    box(fbsx, fbsy, 0.85, (fbx, fby, CY + 5.75), flor)
    gxa, gya = P(-11.6, -(w_hy + 0.80))
    gxb, gyb = P(11.6, -(w_hy + 0.80))
    swag_row(gxa, gya, gxb, gyb, CY + 4.95, 4, 0.98,
             nrm=(inward[0], inward[1], 0), seed=int(abs(cx) * 3 + abs(cy)) + 5)
    if code:
        rsx, rsy = sized((w_hx - WT2) * 2, (w_hy - WT2) * 2)
        region(code, "gate" if gate else "room", "rect", cx, cy, rsx, rsy,
               "a passage through the curtain" if gate else
               "one room: carpet, curtain at the door, two lamps, three niches")
    dsx, dsy = sized(w_hx - 0.5, w_hy - 0.5)
    dentils(cx, cy, dsx, dsy, W1 - 0.55, stone)

    parapet(cx, cy, sized(w_hx - 2.3, w_hy - 2.3)[0], sized(w_hx - 2.3, w_hy - 2.3)[1],
            W1 + W2 + W3, stone)
    dome(cx, cy, W1 + W2 + W3, 5.2, 9.5, ribs=14, seg=36)
    for sa in (-1, 1):
        ex, ey = P(sa * 9.5, 0)
        sphere(1.5, (ex, ey, W1 + W2 + W3 + 1.7), gold if GOLDSMALL else sapph,
               seg=14, rings=9, zscale=1.35)


def corner_tower(cx, cy, code=""):
    H = 30.0
    if code:
        region(code, "tower", "circle", cx, cy, 7.8 * 2, 7.8 * 2,
               "round room at the foot, eight sides, one door to the court")
    cyl(10.2, 2.0, (cx, cy, 1.0), stone, verts=8, smooth=False)
    # the ground five metres are a ROOM: eight wall segments with a door
    # gap toward the court diagonal, a floor, and the shaft solid above
    droom_h = 5.2
    da = math.atan2(62 - cy, 0 - cx)              # the door faces the court
    # HIS "RANDOM OPENINGS". The gap was cut at the nearest of the eight wall
    # segments while the door itself was set at the true bearing to the court -
    # up to fifteen degrees apart - so every tower had a doorway standing
    # beside a hole. The bearing is snapped to a segment now, and they agree.
    da = (round(da / (2 * math.pi) * 8 - 0.5) % 8 + 0.5) / 8 * 2 * math.pi
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
    box(17.4, 17.4, 0.5, (cx, cy, CY - 0.25), stone)
    col(cx, cy, CY - 0.25, 8.7, 8.7, 0.25)
    apx = cx + math.cos(da) * 13.0
    apy = cy + math.sin(da) * 13.0
    box(11.0, 11.0, CY, (apx, apy, CY / 2), stone)          # ground at its door
    col(apx, apy, CY / 2, 5.5, 5.5, CY / 2)
    cyl(10.2, 2.0, (cx, cy, 1.0), stone, verts=8, smooth=False)
    col(cx, cy, 1.0, 7.2, 7.2, 1.0)
    arch(cx + math.cos(da) * 9.0, cy + math.sin(da) * 9.0, 2.0, 2.6, 4.2, 1.0,
         stone, frame=0.45, lit=None, face=(math.cos(da), math.sin(da)))
    door_leaves(cx + math.cos(da) * 8.6, cy + math.sin(da) * 8.6, 2.0, 2.3, 3.6,
                face=(math.cos(da), math.sin(da)), ajar=0.7)
    carpet(cx, cy, CY, 7.4, 9.0, yaw=da + math.pi / 2)
    curtain(cx + math.cos(da) * 7.7, cy + math.sin(da) * 7.7, CY + 4.6, 2.4, 4.6,
            face=(math.cos(da), math.sin(da)))
    for ll in (-3.5, 3.5):
        lantern(cx + ll, cy, 2.0 + droom_h - 0.1, drop=1.9, r=0.26,
                power=0.6, reach=9.0)
    for k9 in range(4):
        a9 = da + math.pi / 2 + k9 * math.pi / 2.4
        sconce(cx + math.cos(a9) * 7.5, cy + math.sin(a9) * 7.5, CY + 2.30,
               (-math.cos(a9), -math.sin(a9)), power=0.5, reach=8.0)
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


_n = [0]


def _code(pre):
    _n[0] += 1
    return "%s%d" % (pre, _n[0])


for sxm in (-1, 1):
    for i in range(3):
        module(sxm * (38 + 30 * i), 0, (0, -1), gate=(i == 0),
               code=("S%s%d" % ("W" if sxm < 0 else "E", i + 1)))
for i in range(5):
    for sxm in (-1, 1):
        module(sxm * 100, 12 + 30 * i, (sxm, 0),
               code=("%s%d" % ("W" if sxm < 0 else "E", i + 1)))
for i in range(7):
    module(-90 + 30 * i, 120, (0, 1), gate=(i == 3), code="N%d" % (i + 1))

for sxm in (-1, 1):
    corner_tower(sxm * 109, -19, code=("TSW" if sxm < 0 else "TSE"))
    corner_tower(sxm * 109, 129, code=("TNW" if sxm < 0 else "TNE"))

for sxm in (-1, 1):
    sd = "W" if sxm < 0 else "E"
    minaret(sxm * 23, -24, 58.0, code="MS" + sd)
    minaret(sxm * 120, 75, 52.0, code="M" + sd)
    connector(sxm * 113, 75, sxm * 118, 75)
    minaret(sxm * 23, 140, 52.0, code="MN" + sd)
    connector(sxm * 23, 133, sxm * 23, 138)

# ============================================================ THE COURT
# paved now, not bare ground - and SOLID
# THE PAVING, widened to meet every wall it is supposed to meet. It used to
# stop four metres short of the south row of rooms and of both corner towers.
box(178, 100, 0.5, (0, 60, CY - 0.25), stone)
col(0, 60, CY - 0.25, 89, 50, 0.25)
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
        cyl(0.5, 7.2, (px, py, CY + 3.6), stone, verts=10)
        cyl(0.66, 0.42, (px, py, CY + 7.0), stone, verts=10)
        col(px, py, CY + 3.6, 0.55, 0.55, 3.6)
    for i in range(n):
        px = x0 + ux * (ln * (i + 0.5) / n)
        py = y0 + uy * (ln * (i + 0.5) / n)
        arch(px, py, CY, ln / n - 0.8, 7.2, 0.7, stone, frame=0.38, lit=None, face=face)
        rose_boss(px + fx0 * 0.30, py + fy0 * 0.30, CY + 6.9, (fx0, fy0, 0), 0.40)
    # The roof of the colonnade runs INTO the curtain behind it. It used to
    # stop at its own depth and left a hairline of daylight along the joint;
    # a roof that only kisses a wall always will. It is carried 0.9m further
    # back, where the wall swallows it.
    ext = 0.9
    bx3 = (x0 + x1) / 2 - fx0 * (RW_D + ext) / 2
    by3 = (y0 + y1) / 2 - fy0 * (RW_D + ext) / 2
    sx3 = abs(dx) + ((RW_D + ext) if fx0 else 1.6)
    sy3 = abs(dy) + ((RW_D + ext) if fy0 else 1.6)
    box(max(sx3, RW_D), max(sy3, RW_D), 0.8, (bx3, by3, CY + 7.4), stone)
    box(max(sx3, RW_D) + 0.6, max(sy3, RW_D) + 0.6, 0.9, (bx3, by3, CY + 8.15), stone)
    # a carved band of leaf over the whole colonnade
    box(abs(dx) + (0.5 if fx0 else 0.44), abs(dy) + (0.44 if fx0 else 0.5), 0.80,
        ((x0 + x1) / 2 + fx0 * 0.30, (y0 + y1) / 2 + fy0 * 0.30, CY + 7.82), flor)
    # HIS FLORAL ROPE: hung from pier to pier, in half circles, all the way
    for i in range(n):
        ga = (x0 + ux * (ln * i / n) + fx0 * 0.66,
              y0 + uy * (ln * i / n) + fy0 * 0.66, CY + 5.55)
        gb = (x0 + ux * (ln * (i + 1) / n) + fx0 * 0.66,
              y0 + uy * (ln * (i + 1) / n) + fy0 * 0.66, CY + 5.55)
        garland(ga, gb, 1.05, nrm=(fx0, fy0, 0), seed=int(abs(x0) + abs(y0)) * 7 + i)
    # torches along the arcade, and a pot of flowers between them
    for i in range(1, n, 5):
        tx = x0 + ux * (ln * i / n) + fx0 * 2.4
        ty = y0 + uy * (ln * i / n) + fy0 * 2.4
        torchpost(tx, ty, CY)
    for i in range(3, n, 5):
        px2 = x0 + ux * (ln * i / n) + fx0 * 2.2
        py2 = y0 + uy * (ln * i / n) + fy0 * 2.2
        plant("p_plantpot", px2, py2, CY, sc=1.25)

riwaq_run(-81, 24.5, 81, 24.5, (0, 1))
riwaq_run(-81, 99.5, 81, 99.5, (0, -1))
riwaq_run(-80.5, 25, -80.5, 99, (1, 0))
riwaq_run(80.5, 25, 80.5, 99, (-1, 0))
region("C", "court", "rect", 0, 60, 178, 100, "the paved court")
region("RS", "riwaq", "rect", 0, 27.2, 162, RW_D, "the south colonnade")
region("RN", "riwaq", "rect", 0, 96.8, 162, RW_D, "the north colonnade")
region("RW", "riwaq", "rect", -77.8, 62, RW_D, 74, "the west colonnade")
region("RE", "riwaq", "rect", 77.8, 62, RW_D, 74, "the east colonnade")

# THE GARDEN. His order: lush - blossom trees and ordinary trees, torches set
# beautifully, many flowers on the ground and thick grass. The beds are the
# palace's own stone; everything that grows in them is a real model, recorded
# for the engine to plant (a welded palace cannot carry a tree).
# MEASURED IN THE GAME, not guessed: a blossom tree is 33 m across and 33 m
# tall, which in a courtyard is a forest giant standing on the flowerbed. And
# fl_white / grass_a are not props at all - they are the single card the
# vegetation instancer copies, 5.6 m wide and 30 cm tall, so planting one puts
# a strip of grass lying flat on the soil. The garden uses the plant models,
# and every family is scaled to what it has to be.
BLOSSOM = ["tree/blossom_2x_1", "tree/blossom_2x_2", "tree/blossom_2x_3"]
BLOSSOM_S = (0.30, 0.42)               # 33 m of tree -> 10 to 14
SHADE = ["tree/olive_2", "tree/fig_3", "tree/plane_1"]
SHADE_S = (0.65, 0.95)
SPIRE = ["tree/cypress_1", "tree/cypress_4"]
SPIRE_S = (0.55, 0.78)
BUSH = ["plant/shrub_1", "plant/shrub_2", "plant/sapling_1", "plant/sapling_2"]
FLOWER = ["plant/poppy_1", "plant/poppy_2", "plant/blossom_1", "plant/blossom_2",
          "plant/lavender_1", "plant/lavender_2"]
FLCOL = ["purple", "white", "yellow", "orange"]
GRASS = ["plant/tuft_1", "plant/tuft_2", "plant/fern_1", "plant/fern_2"]
# FOUR QUARTERS ROUND THE WATER - the chahar bagh. Six thin beds left the
# court reading as a paved yard with hedges in it; four deep quarters with
# clear walks between them read as a garden with a court in the middle of it.
BEDS = [(sxg * 42, 62 + syg * 20, 52.0, 30.0) for sxg in (-1, 1) for syg in (-1, 1)]
BED_TOP = CY + 0.83
for _bi, (_bx, _by, _bw, _bd) in enumerate(BEDS):
    region("Q%d" % (_bi + 1), "garden", "rect", _bx, _by, _bw, _bd,
           "a quarter of the garden: blossom, cypress, olive and fig, "
           "thick grass, flowers, a torch at each corner")
for (bx2, by2, bw, bd) in BEDS:
    box(bw, bd, 1.0, (bx2, by2, CY + 0.25), stone)              # the kerb
    # THE SOIL STANDS PROUD OF ITS KERB. Level with it, the two top faces are
    # the same plane and the stone wins half of every pixel - which is why the
    # flowerbed read as pavement with plants standing on it.
    box(bw - 1.2, bd - 1.2, 0.98, (bx2, by2, CY + 0.34), earth)
    col(bx2, by2, (CY + 0.83) / 2, bw / 2, bd / 2, (CY + 0.83) / 2)
    rr = random.Random(int(bx2 * 131 + by2 * 17) + 991)
    # KEEP OFF THE STONE. Anything sown near the rim leans out over the kerb
    # and reads as a flower growing out of the paving.
    hx2, hy2 = bw / 2 - 4.2, bd / 2 - 4.2

    def spot(m=0.0):
        return (bx2 + rr.uniform(-hx2 + m, hx2 - m), by2 + rr.uniform(-hy2 + m, hy2 - m))

    big = max(2, int(bw * bd / 300))
    for i in range(big):                       # the blossom trees, well spaced
        gx3 = bx2 - hx2 + (2 * hx2) * (i + 0.5) / big + rr.uniform(-1.6, 1.6)
        gy3 = by2 + rr.uniform(-1.8, 1.8)
        plant(rr.choice(BLOSSOM), gx3, gy3, BED_TOP, sc=rr.uniform(*BLOSSOM_S))
    for i in range(max(1, big - 1)):           # and the ordinary trees between
        gx3 = bx2 - hx2 * 0.7 + (1.4 * hx2) * (i + 0.5) / max(1, big - 1)
        gy3 = by2 + rr.choice((-1, 1)) * rr.uniform(3.0, hy2)
        plant(rr.choice(SHADE), gx3, gy3, BED_TOP, sc=rr.uniform(*SHADE_S))
    for sxg2 in (-1, 1):                       # cypresses standing at the ends
        plant(rr.choice(SPIRE), bx2 + sxg2 * (bw / 2 - 2.2), by2, BED_TOP,
              sc=rr.uniform(*SPIRE_S))
        torchpost(bx2 + sxg2 * (bw / 2 + 1.7), by2 - bd / 2 - 1.7, CY)
        torchpost(bx2 + sxg2 * (bw / 2 + 1.7), by2 + bd / 2 + 1.7, CY)
    for _ in range(int(bw * bd / 55)):         # bushes
        gx3, gy3 = spot(0.6)
        plant(rr.choice(BUSH), gx3, gy3, BED_TOP, sc=rr.uniform(1.0, 1.7))
    # TEN TIMES THE FLOWERS, his order - twice over. Two things make it
    # possible. First, they are CARDS, not models: a poppy model is 2,780
    # triangles and fifty thousand of those is a hundred and forty million.
    # Second, the bed is written down as a RECTANGLE and the engine sows it
    # itself from a seed - writing fifty thousand positions into the sidecar
    # made it a four megabyte download for a garden.
    COVER.append({"x": round(bx2, 2), "z": round(-by2, 2), "y": round(BED_TOP, 2),
                  "w": round(hx2 * 2, 2), "d": round(hy2 * 2, 2),
                  "fl": int(bw * bd * 2.8), "gr": int(bw * bd * 3.6),
                  "seed": int(abs(bx2) * 131 + abs(by2) * 7) + 17})
    for _ in range(int(bw * bd / 26)):         # a few real plants among them
        gx3, gy3 = spot()
        plant(rr.choice(FLOWER), gx3, gy3, BED_TOP, sc=rr.uniform(1.1, 1.9))

# THE FOUNTAIN: water INSIDE its rims, calm, faintly lit
region("F", "water", "circle", 0, 62, 14.0, 14.0, "the fountain, two basins")
cyl(7.0, 1.4, (0, 62, CY + 0.7), stone, verts=8, smooth=False)
cyl(6.0, 1.3, (0, 62, CY + 0.75), water, verts=24)
cyl(1.1, 2.6, (0, 62, CY + 1.8), stone, verts=10)
cyl(3.4, 0.9, (0, 62, CY + 3.3), stone, verts=8, smooth=False)
cyl(2.7, 0.85, (0, 62, CY + 3.42), water, verts=20)
cyl(0.5, 1.6, (0, 62, CY + 4.4), stone, verts=10)
sphere(0.62, (0, 62, CY + 5.4), gold, seg=14, rings=9)
col(0, 62, (CY + 1.4) / 2, 7.2, 7.2, (CY + 1.4) / 2)
for _i in range(8):                          # torches round the water
    _a = _i / 8.0 * 2 * math.pi + 0.39
    torchpost(math.cos(_a) * 11.5, 62 + math.sin(_a) * 11.5, CY)

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
            own = pool.uvq.get(poly.index)
            if own:
                for k, li in enumerate(poly.loop_indices):
                    uv.data[li].uv = own[k]
                continue
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
# THE CURTAINS - his pink cloth, one whole repeat of the pattern per panel
parts.append(make_mesh(cloth, (1, 1, 1, 1), 0.74, 0.0,
                       tex="t_curtain_d.jpg", uvs=1.0))
# THE TILED DADO, and the carved floral bands over it
parts.append(make_mesh(tile, (1, 1, 1, 1), 0.30, 0.0,
                       tex="t_zellij_d.jpg", uvs=0.50))
parts.append(make_mesh(flor, (1, 1, 1, 1), 0.62, 0.0,
                       tex="t_floral_d.jpg", uvs=0.95))
# THE GARLANDS: leaf and flower, the one thing in the palace that is alive
parts.append(make_mesh(folia, (0.19, 0.33, 0.17, 1), 0.88, 0.0))
parts.append(make_mesh(bloom, (0.90, 0.46, 0.60, 1), 0.82, 0.0,
                       emis=(0.36, 0.13, 0.21, 1), estr=0.30))
# CANDLELIGHT, not a white block. An emissive at strength three clips every
# channel and comes out white, which is what made every lantern a paper lamp.
parts.append(make_mesh(glow, (1.0, 0.58, 0.22, 1), 0.9, 0.0,
                       emis=(1.0, 0.40, 0.09, 1), estr=0.80))
# the amber panes of the lanterns: lit from within, warm, never white
parts.append(make_mesh(pane, (0.72, 0.40, 0.16, 1), 0.42, 0.0,
                       emis=(0.98, 0.36, 0.08, 1), estr=0.34))
# THE SOIL OF THE BEDS. Flat brown paint read as cardboard under the plants -
# a garden bed is grass and turned earth, and it wants a surface.
parts.append(make_mesh(earth, (0.38, 0.30, 0.21, 1), 1.0, 0.0,
                       tex="g_grass_d.jpg", uvs=2.2))
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
# what each surface costs, so a heavy round can be traced to its pool
for _pl in (stone, gold, wood, rug, cloth, tile, flor, folia, bloom, pane,
            glow, earth, water, sapph, spark, sparkv):
    if _pl.v:
        _t = sum(len(f) - 2 for f in _pl.f)
        print("POOL %-7s %7d verts %7d tris" % (_pl.name, len(_pl.v), _t))

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
for ff in FIRES:
    for k in ("x", "y", "z", "g"):
        ff[k] = round(ff[k] * QSCALE, 2)
for gg in GARDEN:
    for k in ("x", "y", "z"):
        gg[k] = round(gg[k] * QSCALE, 2)
for ll in LAMPS:
    for k in ("x", "y", "z"):
        ll[k] = round(ll[k] * QSCALE, 2)
for cv in COVER:
    for k in ("x", "y", "z", "w", "d"):
        cv[k] = round(cv[k] * QSCALE, 2)
with open(os.path.splitext(OUT)[0] + ".door.json", "w") as f:
    json.dump({"doors": DOORS}, f)
for _r in PLAN:
    for _k in ("x", "y", "a", "b"):
        _r[_k] = round(_r[_k] * QSCALE, 2)
with open(os.path.splitext(OUT)[0] + ".plan.json", "w") as f:
    json.dump({"scale": QSCALE, "regions": PLAN}, f, indent=1)
with open(os.path.splitext(OUT)[0] + ".fx.json", "w") as f:
    json.dump({"fireflies": FLIES, "fires": FIRES, "garden": GARDEN,
               "lamps": LAMPS, "cover": COVER}, f)
print("WROTE", OUT, "doors", len(DOORS), "flies", len(FLIES),
      "fires", len(FIRES), "planted", len(GARDEN), "lamps", len(LAMPS),
      "beds", len(COVER),
      "sown", sum(c["fl"] + c["gr"] for c in COVER), "regions", len(PLAN))
