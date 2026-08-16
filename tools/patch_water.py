"""Makes the water stay put in the world and move like water.

The surface is one big plane that follows the player, which is how an endless
sea is done -- but its UVs came from the plane, so the ripples travelled with
you and the whole surface looked glued to the camera. The fix is to take the UV
from the world position instead, so the pattern belongs to the world; then two
layers of it are scrolled in different directions at different speeds, which is
what makes water read as flowing rather than as a shiny floor.
"""
import pathlib

NEW_WATER = '''  var waterMat = null, waterFlow = null;
  function initWater() {
    var wn = tex('assets/water_n.jpg', false, true);
    var g = new THREE.PlaneGeometry(7000, 7000, 1, 1);
    g.rotateX(-Math.PI / 2);
    var m = new THREE.MeshStandardMaterial({
      color: 0x16203c, roughness: 0.14, metalness: 0.55,
      normalMap: wn, normalScale: new THREE.Vector2(0.55, 0.55),
      transparent: true, opacity: 0.93
    });
    m.onBeforeCompile = function (sh) {
      sh.uniforms.uFlow = { value: 0 };
      waterFlow = sh.uniforms.uFlow;
      sh.vertexShader = 'varying vec3 vWaterPos;\\n' + sh.vertexShader.replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\\n vWaterPos = (modelMatrix * vec4(transformed,1.0)).xyz;'
      );
      sh.fragmentShader = 'uniform float uFlow;\\nvarying vec3 vWaterPos;\\n' + sh.fragmentShader;
      /* Two sheets of ripple, taken from world position so they stay where
         they are however far you walk, drifting at different speeds so the
         pattern never sits still and never repeats visibly. */
      sh.fragmentShader = sh.fragmentShader.replace(
        '#include <normal_fragment_maps>',
        [
          'vec2 wUv = vWaterPos.xz * 0.045;',
          'vec3 nA = texture2D( normalMap, wUv + vec2( uFlow * 0.021, uFlow * 0.013) ).xyz * 2.0 - 1.0;',
          'vec3 nB = texture2D( normalMap, wUv * 0.47 + vec2(-uFlow * 0.011, uFlow * 0.024) ).xyz * 2.0 - 1.0;',
          'vec3 nC = texture2D( normalMap, wUv * 2.3 + vec2( uFlow * 0.04, -uFlow * 0.031) ).xyz * 2.0 - 1.0;',
          'vec3 mapN = normalize(nA + nB * 0.8 + nC * 0.35);',
          'mapN.xy *= normalScale;',
          'normal = normalize( tbn * mapN );'
        ].join('\\n'));
    };
    water = new THREE.Mesh(g, m);
    water.position.y = WATER_Y;
    water.renderOrder = 1;
    waterMat = m;
    scene.add(water);
    W.water = water;
  }
  W.tickWater = function (t) { if (waterFlow) waterFlow.value = t; };
'''


def main():
    p = pathlib.Path("js/world.js")
    s = p.read_text(encoding="utf-8")
    if "vWaterPos" in s:
        print("water already in world space")
        return

    start = s.index("  function initWater() {")
    end = s.index("  /* ------------------------------------------------------------ physics */")
    s = s[:start] + NEW_WATER + "\n" + s[end:]

    # drive the flow from the frame clock
    old = "    if (W.tick) W.tick(W, dt, clock.elapsedTime);"
    new = "    if (W.tickWater) W.tickWater(clock.elapsedTime);\n" + old
    assert old in s
    s = s.replace(old, new, 1)

    p.write_text(s, encoding="utf-8")
    print("water is world-space and flowing")


if __name__ == "__main__":
    main()
