"""What is actually expensive in the world.

Reads every runtime GLB, counts its triangles, and reports the heaviest, so
the lag hunt is done on numbers rather than on impressions.

    python tools/audit_cost.py
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "assets", "models")


def gltf_json(path):
    with open(path, "rb") as f:
        head = f.read(20)
        if head[:4] != b"glTF":
            return None
        jlen = struct.unpack("<I", head[12:16])[0]
        f.seek(20)
        return json.loads(f.read(jlen).decode("utf-8", errors="replace"))


def tri_count(j):
    """Triangles, from the accessor counts the primitives point at."""
    acc = j.get("accessors", [])
    total = 0
    for m in j.get("meshes", []):
        for pr in m.get("primitives", []):
            if "indices" in pr and pr["indices"] < len(acc):
                total += acc[pr["indices"]].get("count", 0) // 3
            else:
                pos = (pr.get("attributes") or {}).get("POSITION")
                if pos is not None and pos < len(acc):
                    total += acc[pos].get("count", 0) // 3
    return total


def main():
    rows = []
    for dp, _dn, fs in os.walk(MODELS):
        for f in fs:
            if not f.endswith(".glb"):
                continue
            p = os.path.join(dp, f)
            try:
                j = gltf_json(p)
            except Exception:
                continue
            if not j:
                continue
            key = os.path.relpath(p, MODELS).replace("\\", "/")[:-4]
            names = ",".join(m.get("name", "")[:18] for m in j.get("meshes", [])[:2])
            rows.append((tri_count(j), os.path.getsize(p) // 1024, key, len(j.get("meshes", [])), names))
    rows.sort(reverse=True)
    print("%-34s %9s %8s %6s  %s" % ("model", "tris", "kB", "meshes", "first mesh names"))
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 22
    for t, kb, key, nm, names in rows[:n]:
        print("%-34s %9d %8d %6d  %s" % (key, t, kb, nm, names))
    print("\ntotal models %d, total tris %d" % (len(rows), sum(r[0] for r in rows)))


if __name__ == "__main__":
    main()
