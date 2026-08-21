/* THE SOUND OF THE STONES.
   =================================================================
   Synthesised, not sampled. A sparkle is a handful of very short bell tones
   an octave or two above anything else in the scene, struck almost together
   and dying at different rates - and that is easier to BUILD than to find, it
   downloads nothing, and it can be varied every single time so that fifty
   swings do not sound like one swing played fifty times.

   What makes a struck-metal sound rather than a beep:
     * the partials are INHARMONIC. A bell's overtones are not whole multiples
       of its fundamental; they sit at odd ratios, which is exactly why a bell
       sounds like a bell and a sine sounds like a test tone.
     * the high partials die FIRST. Energy leaves the small modes fastest, so
       the sound gets darker as it fades. Give every partial the same decay
       and it reads as a synthesiser.
     * the attack is not instant. A few milliseconds of rise stops the click.

   Nothing is created until she asks for a sound, because a browser will not
   let an AudioContext start before she has touched the page anyway. */
(function () {
  'use strict';
  var W = window.W = window.W || {};

  var ctx = null, bus = null, muted = false;

  function boot() {
    if (ctx) return ctx;
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    try { ctx = new AC(); } catch (e) { return null; }
    bus = ctx.createGain();
    bus.gain.value = 0.32;               /* it is jewellery, not a cymbal */
    /* a gentle shelf off the very top, or it is glassy and tiring */
    var lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 9000;
    lp.Q.value = 0.4;
    bus.connect(lp);
    lp.connect(ctx.destination);
    return ctx;
  }

  function wake() {
    if (!ctx) return;
    if (ctx.state === 'suspended') ctx.resume();
  }
  W.sfxWake = wake;

  /* the inharmonic partials of a small struck bell, as ratios */
  var PARTIALS = [1.0, 2.76, 5.40, 8.93, 13.34];
  var DECAY = [1.00, 0.62, 0.44, 0.30, 0.22];

  function chime(f0, when, gain, len) {
    if (!ctx) return;
    for (var i = 0; i < PARTIALS.length; i++) {
      var o = ctx.createOscillator();
      o.type = i === 0 ? 'triangle' : 'sine';
      o.frequency.value = f0 * PARTIALS[i] * (1 + (Math.random() - 0.5) * 0.006);
      var g = ctx.createGain();
      var a = 0.004 + Math.random() * 0.004;
      var d = len * DECAY[i];
      var lvl = gain * (i === 0 ? 1.0 : 0.42 / (i + 0.4));
      g.gain.setValueAtTime(0.0001, when);
      g.gain.exponentialRampToValueAtTime(Math.max(lvl, 0.0002), when + a);
      g.gain.exponentialRampToValueAtTime(0.0001, when + a + d);
      o.connect(g);
      g.connect(bus);
      o.start(when);
      o.stop(when + a + d + 0.02);
    }
  }

  /* ------------------------------------------------------------ a sparkle
     Several stones catching the light at once: a small scatter of chimes
     over a tenth of a second, spread across a pentatonic set so that no two
     ever grate against each other however they land. */
  var SCALE = [1.0, 1.125, 1.25, 1.5, 1.6875, 2.0, 2.25, 2.5, 3.0];

  W.sfxSparkle = function (opt) {
    opt = opt || {};
    if (muted || !boot()) return;
    wake();
    var n = opt.n || (4 + (Math.random() * 4) | 0);
    var base = opt.base || 1480;
    var t0 = ctx.currentTime + 0.002;
    var vol = (opt.gain === undefined ? 1 : opt.gain);
    for (var i = 0; i < n; i++) {
      var f = base * SCALE[(Math.random() * SCALE.length) | 0];
      /* an octave up now and then, which is what gives it its glitter */
      if (Math.random() < 0.30) f *= 2;
      chime(f,
            t0 + Math.random() * (opt.spread || 0.11),
            vol * (0.10 + Math.random() * 0.16),
            (opt.len || 0.75) * (0.55 + Math.random() * 0.9));
    }
  };

  /* one stone, for a single shed - quieter and lower than a whole handful */
  W.sfxChime = function (gain) {
    if (muted || !boot()) return;
    wake();
    chime(1180 * SCALE[(Math.random() * SCALE.length) | 0],
          ctx.currentTime + 0.002, (gain || 1) * 0.09,
          0.65 + Math.random() * 0.5);
  };

  /* a long, soft shimmer, for something that is continuously giving off
     light rather than being struck once */
  var lastShimmer = 0;
  W.sfxShimmer = function (t, every) {
    if (muted) return;
    if (t - lastShimmer < (every || 0.42)) return;
    lastShimmer = t;
    W.sfxSparkle({ n: 2, base: 1760, gain: 0.42, spread: 0.06, len: 1.1 });
  };

  W.sfxMute = function (on) { muted = !!on; };
  W.sfxMuted = function () { return muted; };

  /* the browser will not start audio until she has touched the page */
  ['pointerdown', 'keydown', 'touchstart'].forEach(function (e) {
    window.addEventListener(e, function () { boot(); wake(); }, { once: true });
  });
})();
