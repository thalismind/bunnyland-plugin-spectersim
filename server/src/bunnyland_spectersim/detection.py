"""Detection consequence: drive detector volume + audible noise from same-room markers.

Runs each tick (registered via :func:`bunnyland_spectersim.install.install_spectersim`).
For every detector it:

1. resolves the detector's room (works whether the device is held or resting on the floor),
2. sums the strength of matching markers in that room,
3. sets ``volume = gain * detected_loudness`` when powered, else ``0``, and
4. **pulses** a short-lived ``NoiseComponent`` entity in the room whenever the audible band
   rises or a re-pulse interval elapses, so the server's own ``HearingConsequence`` delivers
   the beep/wail/hiss to everyone present.

The noise is always a *dedicated throwaway entity* — never a component on the detector —
because ``HearingConsequence`` removes expired noise entities outright.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import NoiseComponent, spawn_entity
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent
from relics import World

from .bands import SILENT, band_rank, detected_loudness, volume_band
from .components import DETECTOR_MARKER_PAIRS
from .spatial import room_of

#: How long a pulsed noise entity lives, in epoch (world-second) units. Comfortably longer
#: than one tick so the hearing pipeline sees it regardless of time scale.
NOISE_TTL = 60

#: While a detector stays in the same audible band, re-pulse at most this often (epochs).
REPULSE_INTERVAL = 30


class DetectionConsequence:
    """Update detector volume and emit audible pulses each tick."""

    def __init__(self, *, noise_ttl: int = NOISE_TTL, repulse_interval: int = REPULSE_INTERVAL):
        self.noise_ttl = noise_ttl
        self.repulse_interval = repulse_interval
        # Per-detector pulse state, keyed by detector id string: (last_band, last_pulse_epoch).
        self._pulses: dict[str, tuple[str, int]] = {}

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        seen: set[str] = set()
        for detector_type, marker_type in DETECTOR_MARKER_PAIRS:
            strength_by_room = self._marker_strength_by_room(world, marker_type)
            for detector in list(world.query().with_all([detector_type]).execute_entities()):
                seen.add(str(detector.id))
                self._update_detector(
                    world, epoch, detector, detector_type, strength_by_room
                )
        # Drop pulse state for detectors that no longer exist so the dict cannot grow forever.
        for stale in [key for key in self._pulses if key not in seen]:
            del self._pulses[stale]
        return []

    def _marker_strength_by_room(self, world: World, marker_type: type) -> dict[str, float]:
        totals: dict[str, float] = {}
        for marked in world.query().with_all([marker_type]).execute_entities():
            room = room_of(world, marked.id)
            if room is None:
                continue
            strength = getattr(marked.get_component(marker_type), "strength", 1.0)
            totals[str(room.id)] = totals.get(str(room.id), 0.0) + strength
        return totals

    def _update_detector(self, world, epoch, detector, detector_type, strength_by_room) -> None:
        component = detector.get_component(detector_type)
        room = room_of(world, detector.id)
        room_key = str(room.id) if room is not None else None
        # A detector should not detect itself and never carries a marker, so no self-exclusion
        # is needed: the strength map only counts marker-bearing entities.
        strength = strength_by_room.get(room_key, 0.0) if room_key is not None else 0.0
        detected = detected_loudness(strength)
        new_volume = component.gain * detected if component.powered else 0.0
        if new_volume != component.volume:
            replace_component(detector, replace(component, volume=new_volume))
        if room_key is not None:
            self._maybe_pulse(world, epoch, detector, component.sound, new_volume, room_key)

    def _maybe_pulse(self, world, epoch, detector, sound, volume, room_key) -> None:
        detector_key = str(detector.id)
        band = volume_band(volume)
        last_band, last_epoch = self._pulses.get(detector_key, (SILENT, None))
        if band == SILENT:
            # Remember silence so the next reaction registers as a rising edge.
            self._pulses[detector_key] = (SILENT, last_epoch)
            return
        rising = band_rank(band) > band_rank(last_band)
        stale = last_epoch is None or (epoch - last_epoch) >= self.repulse_interval
        if not (rising or stale):
            self._pulses[detector_key] = (band, last_epoch)
            return
        spawn_entity(
            world,
            [
                NoiseComponent(
                    loudness=volume,
                    text=sound,
                    source_entity_id=detector_key,
                    room_id=room_key,
                    created_at_epoch=epoch,
                    expires_at_epoch=epoch + self.noise_ttl,
                )
            ],
        )
        self._pulses[detector_key] = (band, epoch)


__all__ = ["DetectionConsequence", "NOISE_TTL", "REPULSE_INTERVAL"]
