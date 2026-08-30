# AMĪRATU AL-ʿULŪM — THE LAW OF THIS REPO

These rules are binding on every session. Each one exists because breaking it
already cost a redo. They are not style preferences; they are the checklist
that stops the owner having to ask three times.

## THE PRIME RULE: A PICTURE OR IT DIDN'T HAPPEN

`RESULT sabre verts=5732` means the script ran. It does not mean the sabre is
right. In one session the sabre was modelled lying on its side, the lectern's
posts rose through the book, the well's blocks were rotated into a cog, and
the wings were rebuilt three times — every one of these shipped because the
build log was treated as success.

**No asset, scene change, or fix may be called done until it has been LOOKED
AT: a rendered close-up, near enough to judge, LIT, from at least two angles.**
For a held item, also look at it in the hand. For a building, also stand
inside it. Use the probe harness (below) — never claim from the build log.

## ONE OBJECT AT A TIME

Build one thing → look at it → fix it → look again → only then start the next.
Four artifacts were once built in a batch and all four carried the same axis
bug. The batch saved twenty minutes and cost two days.

## REFERENCE BEFORE GENERATOR

For anything judged on its looks, FIRST write down (in the generator's
docstring) what the real thing does — from photographs, not memory. Then check
the render against that list item by item. The wood, sandstone and rug came
out right because this was done; the curtains and first wings failed because
it wasn't. The quality bar is Mount & Blade II: Bannerlord — real materials,
real construction, nothing toy-like.

## THE ORGANIC LAW: NO SYMMETRY-PLUS-NOISE

A lathe with jitter is still a lathe. Perfect symmetry plus ±2 cm of random
noise reads as a machined part that shipped damaged — never as cloth, plants,
feathers, or anything grown or draped.

- **Cloth (curtains, awnings, throws): SIMULATE.** Blender headless can run a
  cloth sim and bake one frame. Pin where it is held, let gravity make the
  folds. Folds must be UNEQUAL: deep where gathered, shallow at the hem.
- **Plants and blossom: GROW.** A spray follows a branching rule with unequal
  spacing, petals of different sizes at uneven angles, some curled. Never a
  rosette stamp (five petals at exactly 72°).
- **Feathers/wings: the SILHOUETTE comes first.** A wing is one continuous
  curved shape; feathers are layers INSIDE that silhouette, overlapping so no
  daylight shows between them. Feathers radiating from an arc = plucked
  chicken. Build the canopy, then lay the rows on it.
- **A test:** mirror the render left-right. If nothing changes, it is not
  organic yet.

## THE LIVED-IN LAW

Tidy is dead. Every interior and every souk gets a disorder pass, and the
disorder must have a CAUSE: a stool pushed back from the table, a cloth
thrown over a chest half-slipped, a door ajar, wear on the floor at the
doorway, one jar fallen and rolled. Random scatter is not disorder — it reads
as a bug. Grid placement is not order — it reads as a shop display.

## PLACEMENT LAW

- Nothing overlaps another solid. Nothing hovers. Nothing sinks. The audit is
  `W.auditSit()` — run it after any placement change; 0 wrong is the only
  passing score.
- Every "is this spot free?" check goes through `boxClear()` (colliders store
  `cx/cz` and are ROTATED — `b.x` does not exist, and NaN comparisons answer
  "yes" to everything).
- Colliders are STRICT: within ~5 cm of the visible surface. Too big = invisible
  walls; too small = walking through stone. `place()` puts a model's foot
  14 cm below the y it is given — account for it.
- Doors must be real doors: they open, they are recognized (E prompt), their
  collider matches the leaf, and the doorway behind them is clear to walk.

## DESIGN THEME (the owner's standing choices)

- **Night only** in the game. Fire/lamplight is the brightest thing in any
  street; the moon gives direction, never daylight.
- **Aniconic, always.** No faces, figures, animals in any decoration.
- **Relics: baby pink is the dominant colour** of all legendary items; gems
  are twinkling four-pointed STARS (stretched piercing points, never cut
  solids); glow must survive tone mapping (surface ≤ ~1.5 emissive, bloom
  makes the halo).
- Plain, direct English in all player-facing text. Lowercase articles in
  labels. No literary voice.
- 90% realism rule for architecture: real construction logic (lintels,
  courses, joints), with a hand-made softness.

## PERFORMANCE LAW

- This machine is DRAW-CALL bound, not triangle bound (full-detail props at
  15.8M tris measured FASTER than slimmed at 6M). Never slim triangles to
  chase frame time; merge draw calls.
- Anything static welds (crunch). Anything additive/billboarded stays loose
  and must be COUNTED before it is added: every glow, sprite and star is a
  draw call forever.
- Measure with min-of-20 renders or the in-game corner chip. NEVER trust a
  single timing from the hidden browser pane (it swings 33–670 ms on the same
  frame). Draw-call and triangle counts are always exact.
- After ANY model rebuild, run the pipeline **in this order**:
  `python tools/shrink_textures.py; python tools/quantize_glb.py;
  python tools/make_assetindex.py; python tools/check_minaret.py;
  python tools/check_house.py; python tools/bump_version.py`
  then commit + push.

## THE PROBE HARNESS (how to look)

- Serve on 8747; screenshot catcher: `python tools/catch_shot.py` on 8899
  (POST a dataURL to `http://localhost:8899/shots/<name>.png`).
- The pane is often HIDDEN: `innerWidth` is 0 (guard every composer size),
  rAF never fires (drive with `W.stepOnce(dt)` / `W.tickHotbar(dt,t)`),
  screenshots time out (render to canvas and POST instead).
- `W.camState({x,y,z,yaw,pitch})` teleports; `W.touchTerrain(x,z,r)` forces
  streaming; render twice (first call after a move often draws 1 call).
- Blender: `C:\Users\sandk\tools\blender-4.2.1-windows-x64\blender.exe`
  `--background --python <script> -- <args>`. Blender prefixes slot
  materials with `mat_` — the engine matches names, so strip the prefix.

## WORKING WITH THE OWNER

- He gives acceptance criteria in prose. Before building, restate them as
  3–6 mechanical checks in the generator's docstring, and verify each one in
  the render before showing him anything.
- When he says a thing looks wrong ("too shapey", "plucked chicken",
  "disattached"), he is ALWAYS pointing at a real geometric fault. Name the
  fault precisely before touching code; if it can't be named, look harder at
  the picture — do not re-roll and hope.
- Continue non-stop through a task list; don't stop to report between items.
  Commit at every coherent milestone with the reasoning in the message.
