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
