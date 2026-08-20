/* THE FRONT OF THE WORLD: the bar, the shelf, the reader and her page.
   =================================================================
   Three things had to be true for any of this to be worth building.

   1. THE WORLD MUST STOP WHEN A PANEL IS OPEN. The engine's own key handling
      and pointer lock do not know a menu exists, so without this she reads a
      hadith while walking into a wall. Opening a panel releases the pointer,
      tells the engine to idle, and swallows the keys; closing it hands
      everything back.

   2. NOTHING IS WRITTEN TWICE. The text comes from rawda.js, which got it
      from the generated file, which got it from the parsed Bukhari. This file
      formats; it does not carry a single word of the readings.

   3. IT HAS TO BE READABLE OVER A LIT STREET. A translucent panel that looks
      elegant over a still page is unreadable over a torch. The panels are
      nearly opaque, and the bar dims itself while she walks so it is never the
      brightest thing in a night lane. */
(function () {
  'use strict';
  var W = window.W = window.W || {};

  var open = null;                 /* which sheet is up, or null */
  var bar, veil, note, noteT = 0;
  var sheets = {};

  /* --------------------------------------------------------------- making */
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  function sheet(id) {
    var s = el('div', 'sheet');
    s.id = 'sh-' + id;
    s.setAttribute('role', 'dialog');
    s.setAttribute('aria-modal', 'true');
    s.innerHTML =
      '<header><div class="ttl"><span class="ar"></span>' +
      '<span class="en"></span></div>' +
      '<button class="x" type="button" aria-label="Close">&#215;</button></header>' +
      '<div class="body"></div>' +
      '<div class="foot"><span class="l"></span><span class="r"></span></div>';
    s.querySelector('.x').addEventListener('click', function () { close(); });
    document.body.appendChild(s);
    sheets[id] = s;
    return s;
  }

  function title(id, ar, en) {
    sheets[id].querySelector('header .ar').textContent = ar;
    sheets[id].querySelector('header .en').textContent = en;
  }

  function body(id) { return sheets[id].querySelector('.body'); }
  function foot(id) { return sheets[id].querySelector('.foot'); }

  /* ------------------------------------------------- opening and closing
     The engine keeps its own idea of the keys and of the pointer. Both have
     to be handed back and forth or the two fight: she types her name and
     walks north at the same time. */
  function show(id) {
    if (open === id) { close(); return; }
    if (open) sheets[open].classList.remove('on');
    open = id;
    sheets[id].classList.add('on');
    veil.classList.add('on');
    W.UI_OPEN = true;
    try { if (document.pointerLockElement) document.exitPointerLock(); } catch (e) {}
    if (W.setIdle) W.setIdle(1e9);          /* do not let the world sleep */
    if (W.releaseKeys) W.releaseKeys();
    var x = sheets[id].querySelector('.x');
    if (x) x.focus();
  }

  function close() {
    if (open) sheets[open].classList.remove('on');
    open = null;
    veil.classList.remove('on');
    W.UI_OPEN = false;
    if (W.wake) W.wake();
  }

  W.uiOpen = show;
  W.uiClose = close;
  W.uiIsOpen = function () { return open !== null; };

  /* ------------------------------------------------------------- the note */
  function say(ar, en, ms) {
    if (!note) return;
    note.innerHTML = '';
    var a = el('span', 'ar'); a.textContent = ar; note.appendChild(a);
    var b = el('span', 'en'); b.textContent = en; note.appendChild(b);
    note.classList.add('on');
    clearTimeout(noteT);
    noteT = setTimeout(function () { note.classList.remove('on'); }, ms || 4200);
  }
  W.uiSay = say;

  /* --------------------------------------------------------- the shelf */
  function drawShelf() {
    var b = body('shelf');
    b.innerHTML = '';
    var list = el('div', 'shelf');
    var books = W.books();
    if (!books.length) {
      b.appendChild(el('p', '', 'The readings have not loaded.'));
      return;
    }
    books.forEach(function (t) {
      var got = W.bookRead(t.slug), all = t.items.length;
      var v = el('button', 'vol');
      v.type = 'button';
      v.innerHTML =
        '<span class="nm"><span class="ar"></span><span class="en"></span></span>' +
        '<span class="cnt"></span><span class="seal"></span>';
      v.querySelector('.nm .ar').textContent = t.ar;
      v.querySelector('.nm .en').textContent = t.en;
      v.querySelector('.cnt').textContent = got + ' / ' + all;
      v.querySelector('.seal').textContent = W.profile().sealed[t.slug] ? '✧' : '';
      v.addEventListener('click', function () { openBook(t.slug); });
      list.appendChild(v);
    });
    b.appendChild(list);
    var band = W.band();
    foot('shelf').querySelector('.l').textContent =
      band.read + ' of ' + band.total + ' read';
    foot('shelf').querySelector('.r').textContent = band.now.en;
  }

  /* --------------------------------------------------------- the reader
     One reading at a time, and it remembers where she was in each book.
     A reading counts as read when she has it in front of her - not when she
     presses anything - because pressing a button to say you read something is
     a thing a game asks for and a book does not. */
  var atIn = {};
  var cur = null;

  function openBook(slug) {
    var t = W.book(slug);
    if (!t) return;
    cur = slug;
    if (atIn[slug] === undefined) {
      /* start her at the first she has not read, or at the top if she is done */
      var i = 0;
      while (i < t.items.length && W.hasRead(slug, i)) i++;
      atIn[slug] = (i >= t.items.length) ? 0 : i;
    }
    show('read');
    drawReading();
  }
  W.openBook = openBook;

  function drawReading() {
    var t = W.book(cur);
    if (!t) return;
    var i = Math.max(0, Math.min(atIn[cur], t.items.length - 1));
    atIn[cur] = i;
    var it = t.items[i];

    title('read', t.ar, t.en + ' · ' + (i + 1) + ' of ' + t.items.length);

    var b = body('read');
    b.innerHTML = '';
    var box = el('div', 'reading');
    var n = el('p', 'n');
    n.textContent = 'Bukhari ' + it.n + '  ·  juzʼ ' + it.juz + ', p.' + it.page;
    box.appendChild(n);
    var h = el('h3'); h.textContent = it.title; box.appendChild(h);

    var l1 = el('p', 'lbl'); l1.textContent = 'The chain'; box.appendChild(l1);
    var isn = el('div', 'isnad-block'); isn.setAttribute('dir', 'rtl');
    isn.setAttribute('lang', 'ar'); isn.textContent = it.isnad;
    box.appendChild(isn);

    var l2 = el('p', 'lbl'); l2.textContent = 'The words'; box.appendChild(l2);
    var ar = el('div', 'ar-block'); ar.setAttribute('dir', 'rtl');
    ar.setAttribute('lang', 'ar'); ar.textContent = it.ar;
    box.appendChild(ar);

    var l3 = el('p', 'lbl'); l3.textContent = 'In plain English'; box.appendChild(l3);
    var en = el('p', 'en-block'); en.textContent = it.en; box.appendChild(en);

    b.appendChild(box);
    b.scrollTop = 0;

    var f = foot('read');
    f.innerHTML = '';
    var left = el('span', 'l');
    var prev = el('button', 'btn'); prev.type = 'button'; prev.textContent = 'Back';
    prev.disabled = (i === 0);
    prev.addEventListener('click', function () { atIn[cur] = i - 1; drawReading(); });
    var next = el('button', 'btn gold'); next.type = 'button';
    next.textContent = (i === t.items.length - 1) ? 'Done' : 'Next';
    next.addEventListener('click', function () {
      if (i === t.items.length - 1) { close(); show('shelf'); drawShelf(); }
      else { atIn[cur] = i + 1; drawReading(); }
    });
    left.appendChild(prev);
    var right = el('span', 'r');
    right.appendChild(next);
    f.appendChild(left); f.appendChild(right);

    /* having it in front of her is having read it */
    if (W.markRead(cur, i)) refreshTicks();
  }

  /* ------------------------------------------------------------- her page */
  function drawHer() {
    var b = body('her');
    b.innerHTML = '';
    var P = W.profile(), band = W.band();

    var row = el('div', 'band-row');
    var ba = el('span', 'ar'); ba.textContent = band.now.ar; row.appendChild(ba);
    var be = el('span', 'en'); be.textContent = band.now.en; row.appendChild(be);
    b.appendChild(row);

    var to = band.next ? band.next.at : band.total;
    var from = band.now.at;
    var pct = to > from ? Math.min(100, Math.round((band.read - from) / (to - from) * 100)) : 100;
    var m = el('div', 'meter'); var fill = el('i');
    fill.style.width = pct + '%'; m.appendChild(fill); b.appendChild(m);

    var t = el('p', 'toward');
    t.textContent = band.next
      ? (band.read + ' of ' + band.total + ' read · ' + (band.next.at - band.read) +
         ' more to ' + band.next.en)
      : (band.read + ' of ' + band.total + ' read · all of it');
    b.appendChild(t);

    var nm = el('div', 'namer');
    var inp = el('input');
    inp.type = 'text'; inp.maxLength = 28;
    inp.placeholder = 'Your name';
    inp.value = P.name || '';
    inp.setAttribute('aria-label', 'Your name');
    var sv = el('button', 'btn'); sv.type = 'button'; sv.textContent = 'Save';
    sv.addEventListener('click', function () {
      P.name = inp.value.trim().slice(0, 28);
      W.profileSave();
      title('her', P.name || 'صاحبة الرَّوْضَة',
            'Her page');
      say('حُفِظ', 'Saved', 2200);
    });
    nm.appendChild(inp); nm.appendChild(sv);
    b.appendChild(nm);

    var sl = el('p', 'lbl'); sl.textContent = 'Sealed';
    sl.style.cssText = 'font:500 9.5px/1 "EB Garamond",serif;letter-spacing:.19em;' +
      'text-transform:uppercase;color:var(--faint);margin:0 0 10px';
    b.appendChild(sl);
    var seals = el('div', 'seals');
    W.books().forEach(function (t2) {
      var s = el('span', 's' + (P.sealed[t2.slug] ? ' got' : ''));
      s.textContent = (P.sealed[t2.slug] ? '✧ ' : '') + t2.en;
      seals.appendChild(s);
    });
    b.appendChild(seals);

    foot('her').querySelector('.l').textContent =
      P.since ? ('In the Rawda since ' + new Date(P.since).toLocaleDateString()) : '';
    foot('her').querySelector('.r').textContent = '';
  }

  /* ------------------------------------------------------------- the keys */
  function refreshTicks() {
    var band = W.band();
    var t = document.getElementById('ui-tick');
    if (t) t.textContent = band.read + '/' + band.total;
    if (open === 'shelf') drawShelf();
  }
  W.uiRefresh = refreshTicks;

  W.onSeal = function (b) {
    say('خُتِمَ · ' + b.ar, b.en + ' — read to the end', 5200);
  };

  /* --------------------------------------------------------------- build */
  function build() {
    bar = el('div');
    bar.id = 'ui-bar';
    bar.innerHTML =
      '<a class="brand" href="#" id="ui-brand">' +
      '<span class="ar">الرَّوْضَة</span>' +
      '<span class="en">Amīratu al-ʿUlūm</span></a>' +
      '<div id="ui-menu">' +
      '<button type="button" id="ui-shelf">The Readings<span class="tick" id="ui-tick"></span></button>' +
      '<button type="button" id="ui-her">Her Page</button>' +
      '</div>';
    document.body.appendChild(bar);
    bar.querySelector('#ui-brand').addEventListener('click', function (e) {
      e.preventDefault(); close();
    });

    veil = el('div'); veil.id = 'ui-veil';
    veil.addEventListener('click', close);
    document.body.appendChild(veil);

    note = el('div'); note.id = 'ui-note';
    document.body.appendChild(note);

    sheet('shelf'); sheet('read'); sheet('her');
    title('shelf', 'القِرَاءَات', 'The Readings');
    title('her', W.profile().name || 'صاحبة الرَّوْضَة', 'Her page');

    document.getElementById('ui-shelf').addEventListener('click', function () {
      drawShelf(); show('shelf');
    });
    document.getElementById('ui-her').addEventListener('click', function () {
      drawHer(); show('her');
    });

    /* Escape closes whatever is up. Captured, so it reaches here before the
       engine sees it - the engine treats keys as movement. */
    window.addEventListener('keydown', function (e) {
      if (!open) return;
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); return; }
      if (open === 'read') {
        if (e.key === 'ArrowRight') { e.preventDefault(); nudge(1); }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); nudge(-1); }
      }
      /* everything else is swallowed so it cannot drive the player */
      if (e.target && e.target.tagName === 'INPUT') return;
      e.stopPropagation();
    }, true);

    refreshTicks();
  }

  function nudge(d) {
    var t = W.book(cur);
    if (!t) return;
    var i = atIn[cur] + d;
    if (i < 0 || i >= t.items.length) return;
    atIn[cur] = i;
    drawReading();
  }

  /* the bar steps back while she is walking */
  var lastMove = 0;
  W.uiTick = function () {
    if (!bar) return;
    var moving = W.keyHeld && (W.keyHeld('KeyW') || W.keyHeld('KeyA') ||
                               W.keyHeld('KeyS') || W.keyHeld('KeyD'));
    if (moving) lastMove = Date.now();
    var dim = !open && (Date.now() - lastMove < 1400);
    bar.classList.toggle('dim', dim);
  };

  W.uiBuild = build;
})();
