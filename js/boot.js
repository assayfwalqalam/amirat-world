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
    'js/build.js',
    /* rawda.js holds what she has read and where the books stand; ui.js is the
       bar, the shelf, the reader and her page. Both come after build.js
       because both hang off things the engine defines. */
    'js/rawda.js',
    'js/ui.js'
  ];

  function load(list, ver, done) {
    /* They used to be fetched one after another, each waiting for the last to
       arrive before it was even asked for. Measured on the live host that was
       six seconds of nothing but round trips. A dynamically created script is
       async by default; setting async=false makes the browser fetch them all
       at once and still run them in the order they were added, which is the
       order they depend on. */
    var left = list.length;
    if (!left) { done(); return; }
    var finished = false;
    function one() {
      if (--left === 0 && !finished) { finished = true; done(); }
    }
    list.forEach(function (src) {
      var s = document.createElement('script');
      s.src = src + '?v=' + ver;
      s.async = false;
      s.onload = one;
      s.onerror = function () {
        var d = document.getElementById('load');
        if (d) d.textContent = 'Could not load ' + s.src;
        one();
      };
      document.head.appendChild(s);
    });
  }

  function start(ver) {
    /* The scripts were versioned but the ASSETS were not, so a texture that
       changed content without changing its name kept being served from cache
       and the new work never arrived on the player's machine. Everything the
       engine fetches now carries this build number. */
    window.__BUILD = ver;
    /* the stylesheet for the front of the world, versioned like everything
       else so a changed panel is never served from a stale cache */
    var css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = 'css/ui.css?v=' + ver;
    document.head.appendChild(css);

    load(FILES, ver, function () {
      var l = document.getElementById('load');
      if (l) l.style.display = 'none';
      var st = document.getElementById('start');
      if (st) st.style.display = '';
      try { W.start(); } catch (e) {
        if (window.W && W.diag) W.diag('start failed: ' + e.message);
      }
      /* The readings are fetched alongside the world rather than before it:
         they are 217 KB and the world is tens of megabytes, so waiting on them
         would be waiting on nothing. The shelf simply says so until they land. */
      try {
        if (W.uiBuild) W.uiBuild();
        if (W.loadRawda) W.loadRawda().then(function () {
          if (W.uiRefresh) W.uiRefresh();
          if (W.standBooksWhenReady) W.standBooksWhenReady();
        });
      } catch (e) {
        if (window.W && W.diag) W.diag('the front did not build: ' + e.message);
      }
    });
  }

  fetch('version.json?t=' + Date.now(), { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (j) { start(j.build || Date.now()); })
    .catch(function () { start(Date.now()); });
})();
