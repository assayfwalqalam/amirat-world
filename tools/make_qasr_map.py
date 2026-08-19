# Draws the Qasr's layout map from the palace's OWN coordinates.
#   python tools/make_qasr_map.py  ->  shots/qasr_map.svg
#
# make_palace.py writes assets/models/palace/qasr.plan.json as it builds: every
# room and region, in metres, with a short code. This turns that into a plan you
# can read and write names on. Nothing here is drawn by hand, so the map cannot
# drift away from the palace.
#
# North is up. The centre of the sheet is the centre of the great hall.
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, "assets", "models", "palace", "qasr.plan.json")
OUT = os.path.join(ROOT, "shots", "qasr_map.svg")

# how much stone stands round each interior, so the map shows walls and not
# floating floors (module walls 2.8 m a side, tower wall 3.4 m)
WALL_RECT = 5.6
WALL_ROUND = 6.8

INK = "#3a2d33"
STYLE = {
    "hall":    ("#e8cfa0", "#8a6c3c", 1.6),
    "porch":   ("#efdcb6", "#8a6c3c", 1.2),
    "stair":   ("#f0e2c6", "#8a6c3c", 1.0),
    "room":    ("#efe4d6", "#7d6a5c", 1.0),
    "gate":    ("#dccfc0", "#5f5145", 1.4),
    "tower":   ("#dfe0e8", "#67697c", 1.4),
    "minaret": ("#cfc3e2", "#6b5a90", 1.4),
    "riwaq":   ("#e6e2da", "#8b8477", 1.0),
    "garden":  ("#cfe3c2", "#5f7d4a", 1.0),
    "water":   ("#bcd6e6", "#4c7290", 1.2),
    "court":   ("#f7f2e7", "#b9ae9a", 1.0),
}
ORDER = ["court", "riwaq", "garden", "water", "stair", "porch", "hall",
         "room", "gate", "tower", "minaret"]

d = json.load(open(PLAN))
regs = [r for r in d["regions"] if r["shape"] != "none"]
levels = [r for r in d["regions"] if r["shape"] == "none"]

xs, ys = [], []
for r in regs:
    xs += [r["x"] - r["a"] / 2 - WALL_ROUND, r["x"] + r["a"] / 2 + WALL_ROUND]
    ys += [r["y"] - r["b"] / 2 - WALL_ROUND, r["y"] + r["b"] / 2 + WALL_ROUND]
M = 16
X0, X1 = min(xs) - M, max(xs) + M
Y0, Y1 = min(ys) - M, max(ys) + M
Wd, Ht = X1 - X0, Y1 - Y0


def sx(x):
    return x - X0


def sy(y):
    return Y1 - y          # north up


out = []
out.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.1f %.1f" '
           'width="100%%" style="max-width:100%%;height:auto;display:block">'
           % (Wd, Ht))
out.append('<rect x="0" y="0" width="%.1f" height="%.1f" fill="#fbf7ef"/>' % (Wd, Ht))

# a faint 20 m grid, so distances can be read off the sheet
g = []
x = int(X0 // 20) * 20
while x < X1:
    g.append('<line x1="%.1f" y1="0" x2="%.1f" y2="%.1f"/>' % (sx(x), sx(x), Ht))
    x += 20
y = int(Y0 // 20) * 20
while y < Y1:
    g.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (sy(y), Wd, sy(y)))
    y += 20
out.append('<g stroke="#e2dacb" stroke-width="0.5">%s</g>' % "".join(g))


def draw(r, mass):
    """mass=True draws the stone round the room; False draws the room itself"""
    fill, line, lw = STYLE[r["kind"]]
    grow = 0.0
    if mass:
        if r["kind"] not in ("room", "gate", "tower", "minaret"):
            return ""
        grow = WALL_ROUND if r["shape"] == "circle" else WALL_RECT
        fill, line, lw = "#ded3c4", "#6d6055", 1.1
    if r["shape"] == "circle":
        return ('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" '
                'stroke-width="%.1f"/>'
                % (sx(r["x"]), sy(r["y"]), r["a"] / 2 + grow, fill, line, lw))
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1.2" '
            'fill="%s" stroke="%s" stroke-width="%.1f"/>'
            % (sx(r["x"] - r["a"] / 2) - grow / 2, sy(r["y"] + r["b"] / 2) - grow / 2,
               r["a"] + grow, r["b"] + grow, fill, line, lw))


for r in sorted(regs, key=lambda r: ORDER.index(r["kind"])):
    out.append(draw(r, True))
for r in sorted(regs, key=lambda r: ORDER.index(r["kind"])):
    out.append(draw(r, False))

# the codes
for r in regs:
    fs = 7.0 if r["kind"] in ("hall", "court") else 5.2
    out.append('<text x="%.1f" y="%.1f" font-family="Georgia,serif" '
               'font-size="%.1f" font-weight="700" fill="%s" '
               'text-anchor="middle" dominant-baseline="central">%s</text>'
               % (sx(r["x"]), sy(r["y"]), fs, INK, r["code"]))

# north arrow and scale bar
out.append('<g stroke="%s" fill="%s" stroke-width="1.2">' % (INK, INK))
nx, ny = Wd - 26, 26
out.append('<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z"/>'
           % (nx, ny - 13, nx - 5, ny + 4, nx + 5, ny + 4))
out.append('</g>')
out.append('<text x="%.1f" y="%.1f" font-family="Georgia,serif" font-size="7" '
           'fill="%s" text-anchor="middle">N</text>' % (nx, ny + 15, INK))
bx, by = 22, Ht - 20
out.append('<g stroke="%s" stroke-width="1.4"><line x1="%.1f" y1="%.1f" x2="%.1f" '
           'y2="%.1f"/><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
           '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/></g>'
           % (INK, bx, by, bx + 50, by, bx, by - 4, bx, by + 4,
              bx + 50, by - 4, bx + 50, by + 4))
out.append('<text x="%.1f" y="%.1f" font-family="Georgia,serif" font-size="6.5" '
           'fill="%s">50 m</text>' % (bx + 54, by + 2.4, INK))
out.append('</svg>')

open(OUT, "w", encoding="utf-8").write("".join(out))
print("WROTE", OUT, len(regs), "regions +", len(levels), "levels",
      "  sheet %.0f x %.0f m" % (Wd, Ht))
