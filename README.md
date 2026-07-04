# Bunnyland Spectersim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin that adds
paranormal **monster-detecting devices**. A device makes noise (a
wail, a hiss, a buzz, a hum, a beep…) whose **volume rises when entities carrying a
particular marker component share its room**. Two variants ship out of the box:

- **Ghost detector** — reacts to `SpectralMarkerComponent` (monsters, spirits, the undead).
- **Radio** — reacts to `RadioSourceMarkerComponent` (transmitters, beacons, broadcasters).

**v2** bundles two survival-horror mechanics on top of the detectors:

- **Sanity** — a dread meter (`SanityComponent`) that drains near spectral presences and in
  the dark, recovers in safe or bright spirit-free rooms, and injects escalating first-person
  distortion lines ("Your hands won't stop shaking.", whispering, a hallucinated presence)
  into the afflicted character's own prompt.
- **Rituals & wards** — `draw-ward` protects a room and `perform-ritual` channels a held
  ritual kit to weaken and finally banish a spectral presence; a warded room also erodes any
  trapped presence passively.

This repo intentionally keeps all detector work outside the main `bunnyland-server` repo.

## Layout

- `server/` - Python Bunnyland plugin package with the marker/detector components, the
  detection consequence, prompt fragments, a worldgen enrichment hook, the two player/AI
  verbs, spawn factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_spectersim.bunnyland_plugins()` and contributes:

- `SpectralMarkerComponent`, `RadioSourceMarkerComponent` - detectable markers.
- `GhostDetectorComponent`, `RadioDetectorComponent` - the devices.
- `DetectionConsequence` - sets each detector's `volume` from same-room markers every tick
  and pulses a `NoiseComponent` so the device is audible via the server's existing hearing
  pipeline. Works for held **and** floor-resting detectors, as long as they are powered on.
- `spectersim_fragments` - renders device state into both human and AI prompts.
- `SpecterWorldgenHook` - tags generated enemies (and broadcasters) with the markers.
- `power-detector` and `set-detector-volume` - verbs for the holder (human or AI).
- `spawn_ghost_detector`, `spawn_radio` - spawn factories.

v2 additionally contributes:

- `SanityComponent` and `SanityConsequence` - the per-tick dread meter, with band-crossing
  `SanityChangedEvent`s and first-person `sanity_fragments`.
- `WardComponent`, `RitualKitComponent`, and `WardConsequence` - room protection plus the
  passive weaken/banish pass, with `WardDrawnEvent`, `PresenceWeakenedEvent`, and
  `PresenceBanishedEvent`.
- `draw-ward` and `perform-ritual` - verbs for placing wards and banishing presences.
- `ritual_fragments` - renders ward protection and the held-kit line into prompts.
- `spawn_ritual_kit`, `spawn_ward` - spawn factories.

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_spectersim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_spectersim` package must be importable by the server (installed into the
server's environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
