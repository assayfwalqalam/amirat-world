"""Writes assets/manifest.json: every placeable model, grouped for the editor.

Run after generating or adding models. The editor reads this, so anything on
disk shows up in the palette without touching the editor's code.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "assets", "models")

# order matters: the first pattern that matches decides the group
GROUPS = [
    ("Buildings",   [r"^kit/"]),
    ("Buildings",   [r"^bh\d+$", r"^m_mosque$", r"^mosque/"]),
    ("City walls",  [r"^w_"]),
    ("Minarets",    [r"^minaret/"]),
    ("Boundary walls", [r"^bound/"]),
    ("Vehicles",    [r"^veh/"]),
    ("Camp",        [r"^camp/"]),
    ("Books",       [r"^book/"]),
    ("Fences",      [r"^fence/"]),
    ("Market stalls", [r"^stall/"]),
    ("Pottery",     [r"^pot/"]),
    ("Market",      [r"^p_(stall|awning|cart|bench|pergola)$"]),
    ("Containers",  [r"^p_(barrel|barrels|crates|jars|sacks|basket|pot|waterjug|plantpot)$"]),
    ("Household",   [r"^p_(carpet|cushions|table|stool|chest|books|scrolls|inkset|bowl|bread|broom|oillamp|ropecoil|ladder)$",
                     r"^(carpet|mashaf)$"]),
    ("Arms",        [r"^p_(spears|swordrack|bowarrows)$"]),
    ("Fire & light", [r"^p_(torch|torchpost|brazier|firewood)$", r"^lantern$"]),
    ("Trees",       [r"^tree/", r"^(palm|tree_)"]),
    ("Plants",      [r"^plant/", r"^(fl_|grass_|bush_)"]),
    ("Rocks",       [r"^rock/", r"^rock"]),
    ("Other",       [r"^p_"]),
]

NICE = {
    "p_": "", "w_": "", "m_": "", "bh": "House ", "kit/": "",
}


def label(key):
    n = key.split("/")[-1]
    for p in ("p_", "w_", "m_"):
        if n.startswith(p):
            n = n[len(p):]
    n = n.replace("_", " ").strip()
    return n[:1].upper() + n[1:]


def group_of(key):
    for name, pats in GROUPS:
        for p in pats:
            if re.search(p, key):
                return name
    return "Other"


def main():
    keys = []
    for dirpath, _dirs, files in os.walk(MODELS):
        for f in files:
            if not f.endswith(".glb"):
                continue
            if f.endswith(".orig.glb"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), MODELS)
            keys.append(rel[:-4].replace("\\", "/"))

    groups = {}
    for k in sorted(keys):
        g = group_of(k)
        groups.setdefault(g, []).append({"k": k, "n": label(k)})

    order = []
    for name, _ in GROUPS:
        if name in groups and name not in order:
            order.append(name)
    for name in groups:
        if name not in order:
            order.append(name)

    out = {"groups": [{"name": n, "items": groups[n]} for n in order]}
    dest = os.path.join(ROOT, "assets", "manifest.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    total = sum(len(g["items"]) for g in out["groups"])
    print("wrote %s: %d models in %d groups" % (dest, total, len(out["groups"])))
    for g in out["groups"]:
        print("  %-13s %d" % (g["name"], len(g["items"])))


if __name__ == "__main__":
    main()
