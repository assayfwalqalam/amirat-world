"""Gives the land real relief and the ground real surface.

Two complaints, both fair. The land outside the town was one gentle swell with
dunes on it -- no hills worth the name, no mountains, nothing to walk toward.
And the ground read as a flat wash because its texture layers all repeat at
about the same distance, so there was nothing at the scale your eye checks.

Relief now has three separate systems that do not share a mask:
  RIDGES   long mountain chains from ridged noise, with real height
  HILLS    rounded swells, eroded so their flanks are convex not conical
  BENCHES  flat shelves cut into slopes, which is what makes hills look
           geological rather than blobby

Ground gains a stone/scree layer that appears on steep faces, gravel that
gathers in the hollows, and a much finer near-field grain.
"""
import pathlib

RELIEF = '''    /* ------------------------------------------------------------ relief
       Three systems, none sharing a mask, so the land is not one shape
       repeated at different sizes.

       RIDGES  long chains, ridged noise, tall
       HILLS   rounded swells with convex flanks
       BENCH   flat shelves cut into the slopes, which is what stops a hill
               looking like a heap of sand */
    var mountain = ridged(x * 0.00031 - 55.2, z * 0.00031 + 71.8, 4);
    var mMask = sstep(0.52, 0.86, fbm(x * 0.00019 + 13.7, z * 0.00019 - 41.2, 3));
    if (mMask > 0.004) {
      var m2 = ridged(x * 0.00082 + 9.4, z * 0.00082 - 3.1, 3);
      var peak = Math.pow(Math.max(0, mountain - 0.30) / 0.70, 1.55);
      h += peak * 300 * mMask;
      h += Math.pow(Math.max(0, m2 - 0.42), 1.8) * 90 * mMask;
    }

    var swell = fbm(x * 0.00125 - 7.7, z * 0.00125 + 21.3, 4);
    var hMask = sstep(0.34, 0.62, fbm(x * 0.00042 - 61.1, z * 0.00042 + 8.4, 3));
    h += Math.pow(Math.max(0, swell - 0.30) / 0.70, 1.35) * 96 * hMask;

    /* shelves: quantise a little of the height, so slopes step */
    var bench = fbm(x * 0.0007 + 44.4, z * 0.0007 - 12.2, 2);
    var bAmt = sstep(0.45, 0.72, bench) * sstep(24, 70, h);
    if (bAmt > 0.01) {
      var stepH = 11.0;
      var q = Math.floor(h / stepH) * stepH + stepH * 0.5;
      h = lerp(h, q, bAmt * 0.42);
    }

'''

GROUND = '''          /* Scree on the steep faces and gravel in the hollows. Rock does not
             lie evenly: it collects where it falls and washes out of where
             water runs, and showing that is most of what makes ground read. */
          'float steep = smoothstep(0.24, 0.62, slope);',
          'vec3 scree = texture2D(tGrav, wxz * 0.19).rgb * (0.7 + 0.7 * texture2D(tRock, wxz * 0.031).r);',
          'col = mix(col, scree * 0.92, steep * 0.72);',
          'float hollow = 1.0 - smoothstep(0.02, 0.16, slope);',
          'vec3 grit2 = texture2D(tGrav, wxz * 0.33 + vec2(0.4, 0.9)).rgb;',
          'col = mix(col, col * (0.72 + 0.66 * grit2.r), hollow * 0.34 * (1.0 - vColor.r));',
'''


def main():
    p = pathlib.Path("js/world.js")
    s = p.read_text(encoding="utf-8")

    if "RIDGES  long chains" not in s:
        anchor = "    var hill = fbm(x * 0.0021 - 12.5, z * 0.0021 + 8.8, 4);"
        assert anchor in s, "hill anchor missing"
        s = s.replace(anchor, RELIEF + anchor, 1)
        print("relief added")
    else:
        print("relief already there")

    if "Scree on the steep faces" not in s:
        anchor2 = "          'col = mix(col, col * vec3(0.70, 0.76, 0.70), vColor.b * 0.55);',"
        assert anchor2 in s, "ground anchor missing"
        s = s.replace(anchor2, GROUND + anchor2, 1)
        print("ground detail added")
    else:
        print("ground detail already there")

    # a finer near-field layer than before
    s = s.replace("'  vec3 grain = texture2D(tSand, wxz * 0.62).rgb;',",
                  "'  vec3 grain = texture2D(tSand, wxz * 0.62).rgb;',\n"
                  "          '  vec3 fine2 = texture2D(tGrav, wxz * 3.1).rgb;',")
    s = s.replace("'  float g = grain.r * 0.65 + grit.r * 0.35;',",
                  "'  float g = grain.r * 0.48 + grit.r * 0.30 + fine2.r * 0.22;',")

    p.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    main()
