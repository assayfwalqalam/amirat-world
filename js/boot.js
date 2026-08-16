/* Boot: always fetch the current build number, then load that exact build.
   Browsers cache the page itself, which kept serving old worlds. This file is
   loaded with a unique query every visit, so it is never the stale one. */
(function () {
  'use strict';
  var FILES = [
    'js/three.min.js',
    'js/GLTFLoader.js',
    'js/CopyShader.js',
    'js/LuminosityHighPassShader.js',
    'js/EffectComposer.js',
    'js/RenderPass.js',
    'js/ShaderPass.js',
    'js/MaskPass.js',
    'js/UnrealBloomPass.js',
    'js/world.js',
    'js/build.js'
  ];

  function load(list, ver, done) {
    var i = 0;
    (function next() {
      if (i >= list.length) { done(); return; }
      var s = document.createElement('script');
      s.src = list[i++] + '?v=' + ver;
      s.onload = next;
      s.onerror = function () {
        var d = document.getElementById('load');
        if (d) d.textContent = 'Could not load ' + s.src;
        next();
      };
      document.head.appendChild(s);
    })();
  }

  function start(ver) {
    load(FILES, ver, function () {
      var l = document.getElementById('load');
      if (l) l.style.display = 'none';
      var st = document.getElementById('start');
      if (st) st.style.display = '';
      try { W.start(); } catch (e) {
        if (window.W && W.diag) W.diag('start failed: ' + e.message);
      }
    });
  }

  fetch('version.json?t=' + Date.now(), { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) { start(j.build || Date.now()); })
    .catch(function () { start(Date.now()); });
})();
