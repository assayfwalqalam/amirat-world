# Caps every texture packed inside a model, in place.
#   python tools/shrink_textures.py [--cap 512] [--dry]
#
# Why: measured in the live game, the models carried 594 images and 1.06 GB of
# texture memory - 29 of them 2048x2048, because every building packs its own
# copy of the 2k wall photograph. An integrated GPU cannot hold that, so the
# driver swaps textures in and out and the frame time climbs from 26ms to
# 880ms. Shrinking the packed images is the fix that works on every machine
# and needs no canvas at runtime (Brave blanks canvas-sourced textures).
#
# The GLB is rebuilt honestly: every bufferView is re-packed in order with
# 4-byte alignment and its offset rewritten, so accessors keep pointing at
# their own data.
import io, json, os, struct, sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "assets", "models")

CAP_DEFAULT = 512
# props and small furniture never fill the screen: they get less
CAP_SMALL = 256
SMALL_HINTS = ("/p_", "\\p_", "/prop", "/book", "/pot", "/fence", "/camp", "/bound")

args = sys.argv[1:]
DRY = "--dry" in args
CAP = CAP_DEFAULT
if "--cap" in args:
    CAP = int(args[args.index("--cap") + 1])


def cap_for(path):
    p = path.replace("\\", "/").lower()
    for h in SMALL_HINTS:
        if h.replace("\\", "/") in p:
            return CAP_SMALL
    return CAP


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
        chunk = d[p + 8:p + 8 + clen]
        if ctyp[:3] == b"BIN":
            binc = chunk
        p += 8 + clen + ((4 - clen % 4) % 4)
    return js, binc


def write_glb(path, js, binc):
    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    bb = binc + b"\0" * ((4 - len(binc) % 4) % 4)
    total = 12 + 8 + len(jb) + 8 + len(bb)
    out = bytearray()
    out += b"glTF" + struct.pack("<II", 2, total)
    out += struct.pack("<I", len(jb)) + b"JSON" + jb
    out += struct.pack("<I", len(bb)) + b"BIN\0" + bb
    open(path, "wb").write(bytes(out))


def shrink(path):
    got = read_glb(path)
    if not got:
        return None
    js, binc = got
    images = js.get("images", [])
    if not images:
        return None
    views = js.get("bufferViews", [])
    cap = cap_for(path)

    # pull every bufferView out as bytes, in index order
    blobs = []
    for v in views:
        off = v.get("byteOffset", 0)
        blobs.append(bytearray(binc[off:off + v["byteLength"]]))

    changed = 0
    before = after = 0
    for im in images:
        bv = im.get("bufferView")
        if bv is None:
            continue
        raw = bytes(blobs[bv])
        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
        except Exception:
            continue
        w, h = img.size
        before += w * h * 4
        if max(w, h) <= cap:
            after += w * h * 4
            continue
        r = cap / float(max(w, h))
        nw, nh = max(1, int(w * r)), max(1, int(h * r))
        img = img.resize((nw, nh), Image.LANCZOS)
        buf = io.BytesIO()
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img.convert("RGBA").save(buf, format="PNG", optimize=True)
            im["mimeType"] = "image/png"
        else:
            img.convert("RGB").save(buf, format="JPEG", quality=86, optimize=True)
            im["mimeType"] = "image/jpeg"
        blobs[bv] = bytearray(buf.getvalue())
        after += nw * nh * 4
        changed += 1

    if not changed:
        return None
    if DRY:
        return (changed, before, after)

    # re-pack every view in order, 4-byte aligned, rewriting the offsets
    newbin = bytearray()
    for i, v in enumerate(views):
        pad = (4 - len(newbin) % 4) % 4
        newbin += b"\0" * pad
        v["byteOffset"] = len(newbin)
        v["byteLength"] = len(blobs[i])
        newbin += blobs[i]
    js["buffers"][0]["byteLength"] = len(newbin)
    write_glb(path, js, bytes(newbin))
    return (changed, before, after)


total_before = total_after = files = imgs = 0
for dirpath, dirnames, filenames in os.walk(MODELS):
    for fn in sorted(filenames):
        if not fn.endswith(".glb") or fn.endswith(".hi.glb") or fn.endswith(".orig.glb"):
            continue
        p = os.path.join(dirpath, fn)
        res = shrink(p)
        if res:
            c, b, a = res
            files += 1
            imgs += c
            total_before += b
            total_after += a
            print("%-46s %2d images  %6.1f -> %6.1f MB"
                  % (os.path.relpath(p, ROOT), c, b / 1048576.0, a / 1048576.0))

print("\n%d files, %d images shrunk: %.0f MB -> %.0f MB of texture memory%s"
      % (files, imgs, total_before / 1048576.0, total_after / 1048576.0,
         "  (dry run)" if DRY else ""))
