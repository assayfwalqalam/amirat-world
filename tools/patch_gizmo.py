"""Adds the transform gizmo to js/editor.js."""
import pathlib

GIZMO = r"""  /* ------------------------------------------------------------- gizmo
     Handles you grab with the mouse: three arrows to slide along an axis, a
     flat square to slide across the ground, and a ring to turn. Drawn over
     everything and rescaled every frame so it stays the same size on screen
     however far away the thing is. */
  var GIZ = null, gizDrag = null;
  var AXCOL = { x: 0xe0574f, y: 0x7ddc63, z: 0x5b93e8, xz: 0xe0b23c, ry: 0xe0a13c };

  function gizMat(hex) {
    return new T.MeshBasicMaterial({ color: hex, depthTest: false, depthWrite: false,
                                     transparent: true, opacity: 0.95, toneMapped: false });
  }

  function buildGizmo() {
    var g = new T.Group();
    g.renderOrder = 999;
    g.visible = false;

    function arrow(axis, hex) {
      var m = gizMat(hex);
      var sub = new T.Group();
      var shaft = new T.Mesh(new T.CylinderGeometry(0.022, 0.022, 0.78, 8), m);
      shaft.position.y = 0.39;
      var head = new T.Mesh(new T.ConeGeometry(0.075, 0.24, 12), m);
      head.position.y = 0.9;
      var grab = new T.Mesh(new T.CylinderGeometry(0.13, 0.13, 1.05, 6),
                            new T.MeshBasicMaterial({ visible: false }));
      grab.position.y = 0.52;
      sub.add(shaft); sub.add(head); sub.add(grab);
      if (axis === 'x') sub.rotation.z = -Math.PI / 2;
      if (axis === 'z') sub.rotation.x = Math.PI / 2;
      sub.traverse(function (o) {
        o.userData.giz = { mode: 'move', axis: axis };
        o.userData.mat = m;
        o.renderOrder = 999;
      });
      g.add(sub);
      return sub;
    }
    arrow('x', AXCOL.x);
    arrow('y', AXCOL.y);
    arrow('z', AXCOL.z);

    var pm = gizMat(AXCOL.xz);
    pm.side = T.DoubleSide;
    pm.opacity = 0.55;
    var plate = new T.Mesh(new T.PlaneGeometry(0.34, 0.34), pm);
    plate.rotation.x = -Math.PI / 2;
    plate.position.set(0.19, 0.005, 0.19);
    plate.userData.giz = { mode: 'move', axis: 'xz' };
    plate.userData.mat = pm;
    plate.renderOrder = 999;
    g.add(plate);

    var rm = gizMat(AXCOL.ry);
    var ring = new T.Mesh(new T.TorusGeometry(1.05, 0.022, 8, 56), rm);
    ring.rotation.x = Math.PI / 2;
    var rgrab = new T.Mesh(new T.TorusGeometry(1.05, 0.1, 6, 28),
                           new T.MeshBasicMaterial({ visible: false }));
    rgrab.rotation.x = Math.PI / 2;
    ring.userData.giz = { mode: 'turn', axis: 'y' };
    ring.userData.mat = rm;
    rgrab.userData.giz = { mode: 'turn', axis: 'y' };
    rgrab.userData.mat = rm;
    ring.renderOrder = 999; rgrab.renderOrder = 999;
    g.add(ring); g.add(rgrab);

    scene.add(g);
    return g;
  }

  function gizParts() {
    if (!GIZ) return [];
    var out = [];
    GIZ.traverse(function (o) { if (o.isMesh) out.push(o); });
    return out;
  }

  function selCentre() {
    if (!SEL.length) return null;
    var c = new T.Vector3();
    SEL.forEach(function (r) { c.x += r.x; c.y += r.y; c.z += r.z; });
    return c.divideScalar(SEL.length);
  }

  function updateGizmo() {
    if (!GIZ) return;
    var c = selCentre();
    if (!c) { GIZ.visible = false; return; }
    GIZ.visible = true;
    GIZ.position.copy(c);
    GIZ.scale.setScalar(Math.max(0.6, cam.position.distanceTo(c) * 0.11));
  }

  function gizHighlight(part) {
    gizParts().forEach(function (o) {
      if (o.userData.mat) o.userData.mat.opacity = (o.userData.giz &&
        o.userData.giz.axis === 'xz') ? 0.55 : 0.95;
    });
    if (part && part.userData.mat) part.userData.mat.opacity = 1.0;
  }

  function pickGizmo(ev) {
    if (!GIZ || !GIZ.visible) return null;
    var r = pointerRay(ev);
    var hits = r.intersectObjects(gizParts(), true);
    for (var i = 0; i < hits.length; i++) {
      var o = hits[i].object;
      while (o && !o.userData.giz) o = o.parent;
      if (o) return { part: o, giz: o.userData.giz, point: hits[i].point };
    }
    return null;
  }

  function axisPoint(ev, origin, dir) {
    var r = pointerRay(ev);
    var ro = r.ray.origin, rd = r.ray.direction;
    var w0 = new T.Vector3().subVectors(origin, ro);
    var a = dir.dot(dir), b = dir.dot(rd), cc = rd.dot(rd);
    var d = dir.dot(w0), e = rd.dot(w0);
    var den = a * cc - b * b;
    if (Math.abs(den) < 1e-6) return null;
    var t = (b * e - cc * d) / den;
    return new T.Vector3().copy(origin).addScaledVector(dir, t);
  }

  function planePoint(ev, y) {
    var r = pointerRay(ev);
    var ro = r.ray.origin, rd = r.ray.direction;
    if (Math.abs(rd.y) < 1e-6) return null;
    var t = (y - ro.y) / rd.y;
    if (t < 0) return null;
    return new T.Vector3(ro.x + rd.x * t, y, ro.z + rd.z * t);
  }

  function beginGizDrag(ev, hit) {
    var c = selCentre();
    var dir = new T.Vector3(hit.giz.axis === 'x' ? 1 : 0,
                            hit.giz.axis === 'y' ? 1 : 0,
                            hit.giz.axis === 'z' ? 1 : 0);
    var start = null, ang0 = 0;
    if (hit.giz.mode === 'move' && hit.giz.axis !== 'xz') {
      start = axisPoint(ev, c, dir);
    } else if (hit.giz.mode === 'move') {
      start = planePoint(ev, c.y);
    } else {
      var pp = planePoint(ev, c.y);
      if (pp) ang0 = Math.atan2(pp.z - c.z, pp.x - c.x);
    }
    gizDrag = {
      giz: hit.giz, dir: dir, centre: c, start: start, ang0: ang0,
      recs: SEL.map(function (r) { return { r: r, x: r.x, y: r.y, z: r.z, rot: r.rot }; })
    };
  }

  function moveGizDrag(ev) {
    if (!gizDrag) return;
    var g = gizDrag;
    if (g.giz.mode === 'turn') {
      var pp = planePoint(ev, g.centre.y);
      if (!pp) return;
      var ang = Math.atan2(pp.z - g.centre.z, pp.x - g.centre.x);
      var d = -(ang - g.ang0);
      g.recs.forEach(function (s) {
        s.r.rot = s.rot + d;
        if (g.recs.length > 1) {
          var dx = s.x - g.centre.x, dz = s.z - g.centre.z;
          s.r.x = g.centre.x + dx * Math.cos(d) - dz * Math.sin(d);
          s.r.z = g.centre.z + dx * Math.sin(d) + dz * Math.cos(d);
        }
        applyRec(s.r);
      });
      $('ry').value = Math.round(((g.recs[0].r.rot * 180 / Math.PI) % 360 + 360) % 360);
    } else if (g.giz.axis === 'xz') {
      var pp2 = planePoint(ev, g.centre.y);
      if (!pp2 || !g.start) return;
      var dx2 = pp2.x - g.start.x, dz2 = pp2.z - g.start.z;
      g.recs.forEach(function (s) {
        var nx = s.x + dx2, nz = s.z + dz2;
        if (snapGrid) { nx = Math.round(nx / GRID) * GRID; nz = Math.round(nz / GRID) * GRID; }
        s.r.x = nx; s.r.z = nz;
        if (snapGround) s.r.y = W.heightAt(nx, nz);
        applyRec(s.r);
      });
    } else {
      var now = axisPoint(ev, g.centre, g.dir);
      if (!now || !g.start) return;
      var d3 = new T.Vector3().subVectors(now, g.start);
      g.recs.forEach(function (s) {
        var nx = s.x + d3.x * g.dir.x, ny = s.y + d3.y * g.dir.y, nz = s.z + d3.z * g.dir.z;
        if (snapGrid && g.dir.y === 0) {
          nx = Math.round(nx / GRID) * GRID; nz = Math.round(nz / GRID) * GRID;
        }
        s.r.x = nx; s.r.y = ny; s.r.z = nz;
        applyRec(s.r);
      });
    }
    remark(); updateGizmo(); refreshPanel();
  }

  function endGizDrag() {
    if (!gizDrag) return;
    var before = gizDrag.recs;
    var after = before.map(function (b) {
      return { r: b.r, x: b.r.x, y: b.r.y, z: b.r.z, rot: b.r.rot };
    });
    var moved = after.some(function (a, i) {
      return a.x !== before[i].x || a.y !== before[i].y ||
             a.z !== before[i].z || a.rot !== before[i].rot;
    });
    gizDrag = null;
    if (!moved) return;
    push({
      undo: function () {
        before.forEach(function (b) { b.r.x = b.x; b.r.y = b.y; b.r.z = b.z; b.r.rot = b.rot; applyRec(b.r); });
        remark(); updateGizmo(); refreshPanel();
      },
      redo: function () {
        after.forEach(function (a) { a.r.x = a.x; a.r.y = a.y; a.r.z = a.z; a.r.rot = a.rot; applyRec(a.r); });
        remark(); updateGizmo(); refreshPanel();
      }
    });
  }

"""


def main():
    p = pathlib.Path("js/editor.js")
    s = p.read_text(encoding="utf-8")
    anchor = "  /* ---------------------------------------------------------- raycasting */"
    assert anchor in s, "anchor missing"
    s = s.replace(anchor, GIZMO + anchor, 1)

    # the gizmo follows the selection and the camera
    s = s.replace("    refreshPanel(); refreshList();\n  }\n\n  /* ----------------------",
                  "    refreshPanel(); refreshList(); updateGizmo();\n  }\n\n  /* ----------------------", 1)

    # pointer handling: the gizmo is grabbed before anything else
    old = """      if (e.button === 0 && mode === 'select') {
        var hit = pickObject(e);"""
    new = """      if (e.button === 0) {
        var gh = pickGizmo(e);
        if (gh) { beginGizDrag(e, gh); gizHighlight(gh.part); return; }
      }
      if (e.button === 0 && mode === 'select') {
        var hit = pickObject(e);"""
    assert old in s
    s = s.replace(old, new, 1)

    old = """      if (mode === 'place' && ghost) {"""
    new = """      if (gizDrag) { moveGizDrag(e); return; }
      if (!mouse.down) {
        var hov = pickGizmo(e);
        gizHighlight(hov ? hov.part : null);
        if (hov) { renderer.domElement.style.cursor = 'move'; }
        else { renderer.domElement.style.cursor = ''; }
      }
      if (mode === 'place' && ghost) {"""
    assert old in s
    s = s.replace(old, new, 1)

    old = """      var wasDrag = mouse.moved > 6;
      mouse.down = false; mouse.look = false;"""
    new = """      var wasDrag = mouse.moved > 6;
      mouse.down = false; mouse.look = false;
      if (gizDrag) { endGizDrag(); gizHighlight(null); return; }"""
    assert old in s
    s = s.replace(old, new, 1)

    # keep it the right size as the camera moves
    old = """  function editorStep(dt) {
    if (!document.hasFocus()) keys = {};"""
    new = """  function editorStep(dt) {
    if (!document.hasFocus()) keys = {};
    updateGizmo();"""
    assert old in s
    s = s.replace(old, new, 1)

    # build it once the scene exists
    old = """    rc = new T.Raycaster();
    loader = new T.GLTFLoader();"""
    new = """    rc = new T.Raycaster();
    loader = new T.GLTFLoader();
    GIZ = buildGizmo();"""
    assert old in s
    s = s.replace(old, new, 1)

    # the gizmo must never be picked as a scene object
    old = """    var hits = r.intersectObjects(list, true);
    for (var i = 0; i < hits.length; i++) {
      var o = hits[i].object;
      while (o && !o.userData.rec) o = o.parent;"""
    new = """    var hits = r.intersectObjects(list, true);
    for (var i = 0; i < hits.length; i++) {
      var o = hits[i].object;
      if (o.userData.giz) continue;
      while (o && !o.userData.rec) o = o.parent;"""
    assert old in s
    s = s.replace(old, new, 1)

    p.write_text(s, encoding="utf-8")
    print("gizmo wired into the editor")


if __name__ == "__main__":
    main()
