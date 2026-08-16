"""Rebuilds the riad as one block with a court cut out of it.

The first version put four separate ranges round a gap and relied on them
meeting at the corners. They did not read as a courtyard house at all -- from
outside it looked like two long open crates, and the ground floor of the south
range showed as an open bay. This builds the outer shell as one enclosure, cuts
the court out of the middle, and puts an arcade of piers round it, which is
what a riad actually is.
"""
import pathlib

NEW = '''def build_riad():
    """Two storeys of rooms wrapped round a small inner court."""
    W = random.uniform(17, 22)
    D = random.uniform(15, 20)
    cw = W * random.uniform(0.30, 0.38)          # the court
    cd = D * random.uniform(0.30, 0.38)
    h = random.uniform(3.2, 3.8)

    floor_slab(0, 0, W, D, 0)

    for lvl in range(2):
        z = 0.4 + lvl * (h + 0.4)
        # the outer enclosure: one ring of wall all the way round
        door = ('S', random.uniform(-W * 0.18, W * 0.18), 1.6, 2.6) if lvl == 0 else None
        storey(0, 0, W, D, z, h, doorway=door, wins=random.randint(2, 4),
               roomspot=(lvl == 0))
        # the court: a hole through this floor, walled on all four sides
        for sy in (-1, 1):
            solid(cw + T * 2, T, h, (0, sy * (cd / 2 + T / 2), z + h / 2))
        for sx in (-1, 1):
            solid(T, cd, h, (sx * (cw / 2 + T / 2), 0, z + h / 2))
        # the floor of the storey above, with the court left open in it
        band_d = (D - cd) / 2
        band_w = (W - cw) / 2
        for sy in (-1, 1):
            floor_slab(0, sy * (cd / 2 + band_d / 2), W, band_d, z + h)
        for sx in (-1, 1):
            floor_slab(sx * (cw / 2 + band_w / 2), 0, band_w, cd, z + h)
        if lvl == 0:
            beams(0, -(cd / 2 + band_d / 2), W, band_d, z + h + 0.2)
            SPOTS.append({"c": [0.0, round(z, 3), round(cd / 2 + band_d / 2, 3)],
                          "r": [round(W / 2 - 2, 2), round(band_d / 2 - 1.2, 2)], "k": "room"})
        else:
            SPOTS.append({"c": [0.0, round(z, 3), round(-(cd / 2 + band_d / 2), 3)],
                          "r": [round(W / 2 - 2, 2), round(band_d / 2 - 1.2, 2)], "k": "balcony"})

    ztop = 0.4 + 2 * (h + 0.4)
    # the roof terrace, with the court still open through it
    for sy in (-1, 1):
        band_d = (D - cd) / 2
        parapet(0, sy * (cd / 2 + band_d / 2), W, band_d, ztop, 0.95, rails=(sy < 0))
        SPOTS.append({"c": [0.0, round(ztop, 3), round(-sy * (cd / 2 + band_d / 2), 3)],
                      "r": [round(W / 2 - 1.4, 2), round(band_d / 2 - 1.0, 2)], "k": "roof"})
    for sx in (-1, 1):
        band_w = (W - cw) / 2
        parapet(sx * (cw / 2 + band_w / 2), 0, band_w, cd, ztop, 0.95, rails=False)
    # a low kerb round the court opening on the roof, so nobody walks off it
    for sy in (-1, 1):
        solid(cw + 1.0, 0.28, 0.55, (0, sy * (cd / 2 + 0.14), ztop + 0.28))
    for sx in (-1, 1):
        solid(0.28, cd, 0.55, (sx * (cw / 2 + 0.14), 0, ztop + 0.28))

    # the arcade of piers standing in the court, carrying the upper walk
    n_x = max(2, int(cw / 2.4))
    n_y = max(2, int(cd / 2.4))
    for i in range(n_x + 1):
        px = -cw / 2 + i * (cw / n_x)
        for sy in (-1, 1):
            pillar(px, sy * (cd / 2 - 0.55), 0.4, h - 0.35, r=0.24)
    for i in range(1, n_y):
        py = -cd / 2 + i * (cd / n_y)
        for sx in (-1, 1):
            pillar(sx * (cw / 2 - 0.55), py, 0.4, h - 0.35, r=0.24)

    # what stands in a courtyard: a basin, and somewhere to sit
    cyl(1.05, 1.15, 0.42, (0, 0, 0.61), verts=16, collide=True)
    cyl(0.85, 0.85, 0.1, (0, 0, 0.83), verts=16)
    cyl(0.16, 0.12, 0.5, (0, 0, 1.05), verts=10)
    SPOTS.append({"c": [0.0, 0.4, 0.0],
                  "r": [round(cw / 2 - 0.9, 2), round(cd / 2 - 0.9, 2)], "k": "court"})
    ext_stair(-W / 2 + 0.9, -D / 2 - 2.8, 1.5, 2.6, 0, 0.4 + h)
'''


def main():
    p = pathlib.Path("tools/make_building.py")
    s = p.read_text(encoding="utf-8")
    start = s.index("def build_riad():")
    end = s.index("def build_block():")
    s = s[:start] + NEW + "\n\n" + s[end:]
    p.write_text(s, encoding="utf-8")
    print("riad rebuilt as an enclosure with a court cut into it")


if __name__ == "__main__":
    main()
