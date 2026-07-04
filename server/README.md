# bunnyland-spectersim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_spectersim`.

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_spectersim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `SpectralMarkerComponent`, `RadioSourceMarkerComponent` (markers);
  `GhostDetectorComponent`, `RadioDetectorComponent` (devices).
- **A detection consequence** that sets each detector's `volume` from same-room markers
  every tick and pulses a `NoiseComponent` so the device is audible via the core hearing
  pipeline. Works for held and floor-resting detectors alike.
- **Prompt fragments** rendering the device state into both human and AI prompts.
- **A worldgen hook** tagging generated enemies (and broadcasters) with the markers.
- **Two verbs** — `power-detector` and `set-detector-volume` — usable by the holder
  (human or AI).
- **Spawn factories** — `spawn_ghost_detector`, `spawn_radio`.

### v2 — sanity and rituals

- **Sanity** — `SanityComponent(current, maximum)` on characters and a per-tick
  `SanityConsequence` that drains sanity near `SpectralMarkerComponent` entities and in dark
  rooms, recovers it in safe or bright spirit-free rooms (clamped `0..maximum`), and emits a
  `SanityChangedEvent` on band crossings. `sanity_fragments` inject escalating first-person
  distortion lines at low sanity (shaking, whispering, and a hallucinated presence at
  critical), visible only to the afflicted character.
- **Rituals & wards** — `WardComponent` marks a room (or a placed ward entity) as protected;
  `RitualKitComponent` is a held banishing tool. `WardConsequence` passively weakens then
  banishes (strips the `SpectralMarkerComponent` from) any presence caught in a warded room.
  Verbs `draw-ward` (place a ward, optionally consuming a held reagent) and `perform-ritual`
  (channel a held kit to weaken/banish a presence in the room) emit `WardDrawnEvent`,
  `PresenceWeakenedEvent`, and `PresenceBanishedEvent`. `ritual_fragments` render ward
  protection and the held-kit line.
- **Spawn factories** — `spawn_ritual_kit`, `spawn_ward`.

### v3 — evidence log and fog

- **EVP / evidence log** — `EvidenceComponent` marks a held EVP recorder; `EvidenceLogComponent`
  is an investigator's private, append-only log of captured evidence (EVP captures, cold spots,
  orb sightings, apparition glimpses, detector spikes). The `log-reading` verb captures whatever
  the room currently holds — a `SpectralMarkerComponent` presence and/or an audibly reacting
  detector — into the investigator's log and emits an `EvidenceRecordedEvent`; it rejects with
  `there is nothing to record here` in a quiet room. Evidence content is deterministic (derived
  from stable ids + the world epoch via SHA-1, never `random`/time). `evidence_fragments` surface
  a first-person tally ("Your evidence log holds 3 EVP captures, 1 cold spot.") plus the held-recorder line.
- **Fog** — `FogComponent(density)` sits on a room. A per-tick `FogConsequence` thickens fog in
  the dark (reusing the environment's light level, which the day/night cycle drops at night) and
  near spectral presences, thins it in a bright spirit-free room (clamped `0..1`), and emits a
  `FogChangedEvent` on band crossings (clear/haze/fog/thick). `perceive_through_fog` reuses the
  core perception projection and shrinks it — fewer visible entities as fog thickens, exits
  obscured entirely past the fog band. `fog_fragments` describe the murk to anyone in the room.
- **Spawn factories** — `spawn_recorder`.
