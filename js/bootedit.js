/* Boot for the editor. Same cache-defeating trick as the game: fetch the build
   number first, then load exactly that build. The editor loads the engine but
   not build.js, because the editor is what places things. */
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
    'js/editor.js'
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

  fetch('version.json?t=' + Date.now(), { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) { go(j.build || Date.now()); })
    .catch(function () { go(Date.now()); });

  function go(ver) {
    load(FILES, ver, function () {
      try { W.startEditor(ver); } catch (e) {
        var d = document.getElementById('diag');
        if (d) d.textContent = 'editor failed: ' + e.message;
      }
    });
  }
})();
