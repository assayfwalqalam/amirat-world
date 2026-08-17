"""Bump the build number so the player's browser fetches the new build.

boot.js reads version.json with cache disabled and stamps that number onto
every script, texture, model and collision file it loads. If it is not bumped,
the browser keeps serving the old world from cache and the work never arrives.

RUN THIS BEFORE EVERY PUSH.

    python tools/bump_version.py
"""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "version.json")

# derive it from the git commit count plus the tree's own mtime spread, so it
# always moves forward without needing a clock the scripts are not allowed
try:
    n = int(subprocess.check_output(["git", "rev-list", "--count", "HEAD"],
                                    cwd=ROOT).decode().strip())
except Exception:
    n = 0
old = 0
if os.path.exists(P):
    try:
        old = int(json.load(open(P)).get("build", 0))
    except Exception:
        old = 0
build = max(old + 1, 1000000 + n * 1000)
json.dump({"build": build}, open(P, "w"))
print("build %d -> %d" % (old, build))
