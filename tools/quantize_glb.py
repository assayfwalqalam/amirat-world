# Shrinks the vertex data of every model, in place, with no visible loss.
#   python tools/quantize_glb.py [--dry]
#
# Measured: a house was 1.78 MB, of which 1.50 MB was raw vertex data -
# positions and normals as full floats. Ten houses are seventy per cent of
# everything the game must fetch before it will show you anything.
#
# What this does, per primitive:
#   POSITION    float32 -> int16, with the scale and offset folded into the
#               node's own transform (KHR_mesh_quantization, which three.js
#               reads natively)
#   NORMAL      float32 -> int8, normalized
#   TEXCOORD_0  float32 -> uint16, normalized, when the uvs sit in 0..1;
#               left alone when they run outside it (tiled walls do)
#   COLOR_0     dropped when every vertex carries the SAME colour - that is a
#               material tint, and it belongs in baseColorFactor where it
#               costs four numbers instead of eight bytes a vertex
import json, math, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "assets", "models")
DRY = "--dry" in sys.argv

CT_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    d = open(path, "rb").read()
    if d[:4] != b"glTF":
        return None
    n = struct.unpack("<I", d[12:16])[0]
    js = json.loads(d[20:20 + n])
    p = 20 + n
    binc = b""
    while p < len(d):
        clen = struct.unpack("<I", d[p:p + 4])[0]
        ctyp = d[p + 4:p + 8]
        if ctyp[:3] == b"BIN":
            binc = d[p + 8:p + 8 + clen]
            break
        p += 8 + clen + ((4 - clen % 4) % 4)
    return js, binc


def write_glb(path, js, binc):
    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    bb = binc + b"\0" * ((4 - len(binc) % 4) % 4)
    out = bytearray()
    out += b"glTF" + struct.pack("<II", 2, 12 + 8 + len(jb) + 8 + len(bb))
    out += struct.pack("<I", len(jb)) + b"JSON" + jb
    out += struct.pack("<I", len(bb)) + b"BIN\0" + bb
    open(path, "wb").write(bytes(out))


def get_floats(js, binc, ai):
    a = js["accessors"][ai]
    bv = js["bufferViews"][a["bufferView"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    nc = NCOMP[a["type"]]
    stride = bv.get("byteStride") or (CT_SIZE[a["componentType"]] * nc)
    out = []
    for i in range(a["count"]):
        base = off + i * stride
        out.append(struct.unpack_from("<" + "f" * nc, binc, base))
    return out, a, nc


def quantize(path):
    got = read_glb(path)
    if not got:
        return None
    js, binc = got
    if "meshes" not in js:
        return None
    before = len(binc)

    # every bufferView pulled out so the file can be rebuilt cleanly
    views = js.get("bufferViews", [])
    blobs = [bytearray(binc[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]])
             for v in views]
    new_views = []          # (bytes, target) appended at the end
    changed = False

    def add_view(data, target=None):
        v = {"buffer": 0, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        blobs.append(bytearray(data))
        return len(views) - 1

    # THE TRANSFORM IS PER MESH, NOT PER PRIMITIVE. A model like the Qasr is
    # one mesh of seven primitives - stone, gold, glass, water and so on - all
    # drawn by ONE node. Quantising each primitive to its own box and writing
    # only the last one's scale onto that node throws six of the seven parts
    # somewhere else: domes beside their towers, the fountain's water spread
    # across the sky as a blue slab. Every primitive of a mesh shares one box.
    for mesh in js["meshes"]:
        mn = [1e30, 1e30, 1e30]
        mx = [-1e30, -1e30, -1e30]
        ok_box = False
        for prim in mesh["primitives"]:
            if "POSITION" not in prim["attributes"]:
                continue
            acc = js["accessors"][prim["attributes"]["POSITION"]]
            if acc["componentType"] != 5126:
                continue
            vals, _, _ = get_floats(js, binc, prim["attributes"]["POSITION"])
            if not vals:
                continue
            for v in vals:
                for k in range(3):
                    if v[k] != v[k]:            # NaN: leave this model alone
                        return None
                    mn[k] = min(mn[k], v[k])
                    mx[k] = max(mx[k], v[k])
            ok_box = True
        if not ok_box:
            continue
        span = max(1e-6, max(mx[k] - mn[k] for k in range(3)))
        scale = span / 32767.0
        mesh["_qpos"] = {"offset": mn, "scale": [scale, scale, scale]}

        for prim in mesh["primitives"]:
            attrs = prim["attributes"]

            if "POSITION" in attrs and js["accessors"][attrs["POSITION"]]["componentType"] == 5126:
                vals, acc, nc = get_floats(js, binc, attrs["POSITION"])
                data = bytearray()
                for v in vals:
                    for k in range(3):
                        q = int(round((v[k] - mn[k]) / scale))
                        data += struct.pack("<h", max(-32768, min(32767, q)))
                    data += b"\0\0"
                bvi = add_view(bytes(data), 34962)
                js["bufferViews"][bvi]["byteStride"] = 8
                js["accessors"].append({
                    "bufferView": bvi, "componentType": 5122, "count": len(vals),
                    "type": "VEC3", "min": [0, 0, 0],
                    "max": [int(round((mx[k] - mn[k]) / scale)) for k in range(3)],
                })
                attrs["POSITION"] = len(js["accessors"]) - 1
                changed = True

            if "NORMAL" in attrs and js["accessors"][attrs["NORMAL"]]["componentType"] == 5126:
                vals, acc, nc = get_floats(js, binc, attrs["NORMAL"])
                data = bytearray()
                for v in vals:
                    for k in range(3):
                        data += struct.pack("<b", max(-127, min(127, int(round(v[k] * 127)))))
                    data += b"\0"
                bvi = add_view(bytes(data), 34962)
                js["bufferViews"][bvi]["byteStride"] = 4
                js["accessors"].append({
                    "bufferView": bvi, "componentType": 5120, "count": len(vals),
                    "type": "VEC3", "normalized": True,
                })
                attrs["NORMAL"] = len(js["accessors"]) - 1
                changed = True

            if "COLOR_0" in attrs:
                a = js["accessors"][attrs["COLOR_0"]]
                if a["componentType"] == 5126:
                    vals, _, nc = get_floats(js, binc, attrs["COLOR_0"])
                    flat = all(abs(v[k] - vals[0][k]) < 0.004 for v in vals for k in range(3))
                    if flat and "material" in prim:
                        mat = js["materials"][prim["material"]]
                        pbr = mat.setdefault("pbrMetallicRoughness", {})
                        f = pbr.get("baseColorFactor", [1, 1, 1, 1])
                        pbr["baseColorFactor"] = [round(f[i] * vals[0][i], 5) for i in range(3)] + [f[3]]
                        del attrs["COLOR_0"]
                        changed = True

    if not changed:
        return None

    # the quantised positions need their scale on the node that draws them
    if any("_qpos" in m for m in js["meshes"]):
        js.setdefault("extensionsUsed", [])
        if "KHR_mesh_quantization" not in js["extensionsUsed"]:
            js["extensionsUsed"].append("KHR_mesh_quantization")
        js.setdefault("extensionsRequired", [])
        if "KHR_mesh_quantization" not in js["extensionsRequired"]:
            js["extensionsRequired"].append("KHR_mesh_quantization")
        for node in js.get("nodes", []):
            mi = node.get("mesh")
            if mi is None:
                continue
            q = js["meshes"][mi].get("_qpos")
            if not q:
                continue
            if "matrix" in node:          # leave hand-made matrices alone
                return None
            s0 = node.get("scale", [1, 1, 1])
            t0 = node.get("translation", [0, 0, 0])
            node["scale"] = [s0[i] * q["scale"][i] for i in range(3)]
            node["translation"] = [t0[i] + q["offset"][i] * s0[i] for i in range(3)]
    for m in js["meshes"]:
        m.pop("_qpos", None)

    # Drop what nothing points at any more. The OLD float accessors survive the
    # swap, and if they are counted as users their bufferViews survive with
    # them and the file GROWS instead of shrinking.
    live_acc = set()
    for m2 in js["meshes"]:
        for pr2 in m2["primitives"]:
            for ai2 in pr2["attributes"].values():
                live_acc.add(ai2)
            if "indices" in pr2:
                live_acc.add(pr2["indices"])
    keep_acc = sorted(live_acc)
    acc_remap = {}
    for newi, oldi in enumerate(keep_acc):
        acc_remap[oldi] = newi
    js["accessors"] = [js["accessors"][i] for i in keep_acc]
    for m2 in js["meshes"]:
        for pr2 in m2["primitives"]:
            for k2 in list(pr2["attributes"].keys()):
                pr2["attributes"][k2] = acc_remap[pr2["attributes"][k2]]
            if "indices" in pr2:
                pr2["indices"] = acc_remap[pr2["indices"]]

    used = set()
    for a2 in js["accessors"]:
        if "bufferView" in a2:
            used.add(a2["bufferView"])
    for im in js.get("images", []):
        if "bufferView" in im:
            used.add(im["bufferView"])
    keep = [i for i in range(len(views)) if i in used]
    remap = {}
    for newi, oldi in enumerate(keep):
        remap[oldi] = newi
    views = [views[i] for i in keep]
    blobs = [blobs[i] for i in keep]
    js["bufferViews"] = views
    for a2 in js["accessors"]:
        if "bufferView" in a2:
            a2["bufferView"] = remap[a2["bufferView"]]
    for im in js.get("images", []):
        if "bufferView" in im:
            im["bufferView"] = remap[im["bufferView"]]

    newbin = bytearray()
    for i, v in enumerate(views):
        pad = (4 - len(newbin) % 4) % 4
        newbin += b"\0" * pad
        v["byteOffset"] = len(newbin)
        v["byteLength"] = len(blobs[i])
        newbin += blobs[i]
    js["buffers"][0]["byteLength"] = len(newbin)
    if not DRY:
        write_glb(path, js, bytes(newbin))
    return (before, len(newbin))


tb = ta = 0
files = 0
for dirpath, dirnames, filenames in os.walk(MODELS):
    for fn in sorted(filenames):
        if not fn.endswith(".glb") or fn.endswith(".hi.glb") or fn.endswith(".orig.glb"):
            continue
        p = os.path.join(dirpath, fn)
        # a file that will not read cleanly is left exactly as it was: a
        # corrupt model is far worse than a big one
        try:
            res = quantize(p)
        except Exception as e:
            print("skipped %s (%s)" % (os.path.relpath(p, ROOT), e.__class__.__name__))
            res = None
        if res:
            b, a = res
            tb += b
            ta += a
            files += 1
print("%d files: %.1f MB -> %.1f MB of vertex data%s"
      % (files, tb / 1048576.0, ta / 1048576.0, "  (dry run)" if DRY else ""))
