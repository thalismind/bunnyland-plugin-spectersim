"""Fog: obscuring perception that drifts and thickens over time (v3).

A :class:`FogComponent` sits on a *room* and carries a ``density`` (0..1). A per-tick
:class:`FogConsequence` drifts that density: it **thickens** in the dark (reusing the
environment's light level, which the day/night cycle drops at night) and near spectral
presences, and **thins** in a bright, spirit-free room. As it thickens it *shrinks
perception* — :func:`perceive_through_fog` reuses the core perception projection and then
drops the entities and exits a character can make out, so a fog-bound room hides most of
what is in it.

All banding and drift is deterministic (no ``random`` / wall-clock).
"""

from __future__ import annotations

from dataclasses import replace
from math import ceil

from bunnyland.core import LightComponent
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.projections.perception import Perception, perceive
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import SpectralMarkerComponent
from .spatial import room_of

# --------------------------------------------------------------------------------------
# Tuning
# --------------------------------------------------------------------------------------

#: A room dimmer than this (0..1) counts as dark, and dark air breeds fog.
DARK_LIGHT_THRESHOLD = 0.3

#: Density gained per tick while the room is dark.
THICKEN_DARK = 0.15
#: Extra density gained per tick, per unit of same-room spectral marker strength.
THICKEN_PER_STRENGTH = 0.1
#: Density lost per tick in a bright, spirit-free room.
THIN_PER_TICK = 0.1
#: Fog never exceeds this density.
MAX_DENSITY = 1.0

# Density bands (a higher density is thicker, worse visibility).
CLEAR = "clear"
HAZE = "haze"
FOG = "fog"
THICK = "thick"
HAZE_AT = 0.2
FOG_AT = 0.5
THICK_AT = 0.8

#: Fraction of visible entities that survive each band's obscuring.
_KEEP_FRACTION = {CLEAR: 1.0, HAZE: 0.66, FOG: 0.34, THICK: 0.0}
#: Bands thick enough to hide the room's exits entirely.
_EXITS_HIDDEN_BANDS = frozenset({FOG, THICK})

_BAND_LINES = {
    HAZE: "A thin haze hangs in the air.",
    FOG: "Fog fills the room, softening every edge.",
    THICK: "A thick fog swallows the room; you can barely see.",
}


def fog_band(density: float) -> str:
    """Coarse density band for a fog level (``clear`` is thinnest)."""
    if density < HAZE_AT:
        return CLEAR
    if density < FOG_AT:
        return HAZE
    if density < THICK_AT:
        return FOG
    return THICK


# --------------------------------------------------------------------------------------
# Component
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FogComponent(Component):
    """Obscuring fog on a room. ``density`` runs 0 (clear) to 1 (blinding)."""

    density: float = 0.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        line = _BAND_LINES.get(fog_band(self.density))
        return (line,) if line is not None else ()


# --------------------------------------------------------------------------------------
# Event
# --------------------------------------------------------------------------------------


class FogChangedEvent(DomainEvent):
    """A room's fog crossed into a new density band."""

    density: float
    band: str


# --------------------------------------------------------------------------------------
# Consequence
# --------------------------------------------------------------------------------------


class FogConsequence:
    """Drift each foggy room's density from its dark/spectral surroundings every tick."""

    def __init__(
        self,
        *,
        thicken_dark: float = THICKEN_DARK,
        thicken_per_strength: float = THICKEN_PER_STRENGTH,
        thin_per_tick: float = THIN_PER_TICK,
        dark_threshold: float = DARK_LIGHT_THRESHOLD,
    ):
        self.thicken_dark = thicken_dark
        self.thicken_per_strength = thicken_per_strength
        self.thin_per_tick = thin_per_tick
        self.dark_threshold = dark_threshold

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        strength_by_room = self._spectral_strength_by_room(world)
        events: list[DomainEvent] = []
        for room in list(world.query().with_all([FogComponent]).execute_entities()):
            event = self._update_room(world, epoch, room, strength_by_room)
            if event is not None:
                events.append(event)
        return events

    def _spectral_strength_by_room(self, world: World) -> dict[str, float]:
        totals: dict[str, float] = {}
        for marked in world.query().with_all([SpectralMarkerComponent]).execute_entities():
            room = room_of(world, marked.id)
            if room is None:
                continue
            strength = marked.get_component(SpectralMarkerComponent).strength
            totals[str(room.id)] = totals.get(str(room.id), 0.0) + strength
        return totals

    def _update_room(self, world, epoch, room, strength_by_room):
        fog = room.get_component(FogComponent)
        strength = strength_by_room.get(str(room.id), 0.0)
        dark = self._is_dark(room)

        delta = 0.0
        if dark:
            delta += self.thicken_dark
        if strength > 0.0:
            delta += self.thicken_per_strength * strength
        if delta == 0.0:
            # No stressors: a bright, spirit-free room lets the fog drift away.
            delta = -self.thin_per_tick

        new_density = max(0.0, min(MAX_DENSITY, fog.density + delta))
        if new_density == fog.density:
            return None
        old_band = fog_band(fog.density)
        updated = replace(fog, density=new_density)
        replace_component(room, updated)
        new_band = fog_band(new_density)
        if new_band == old_band:
            return None
        return FogChangedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.ROOM,
                room_id=str(room.id),
                density=new_density,
                band=new_band,
            )
        )

    def _is_dark(self, room) -> bool:
        if not room.has_component(LightComponent):
            return False
        light = room.get_component(LightComponent)
        level = light.level if light.enabled else 0.0
        return level < self.dark_threshold


# --------------------------------------------------------------------------------------
# Perception through fog
# --------------------------------------------------------------------------------------


def perceive_through_fog(world: World, character: Entity) -> Perception:
    """Core perception, then shrunk by the character's current room fog.

    Reuses :func:`bunnyland.projections.perception.perceive` and reduces its result: thicker
    fog reveals fewer entities and, past a threshold, hides the exits entirely.
    """
    perception = perceive(world, character)
    if not perception.can_perceive or perception.room_id is None:
        return perception
    room = room_of(world, character.id)
    if room is None or not room.has_component(FogComponent):
        return perception
    band = fog_band(room.get_component(FogComponent).density)
    if band == CLEAR:
        return perception

    keep = _KEEP_FRACTION[band]
    visible_count = ceil(len(perception.entities) * keep)
    entities = perception.entities[:visible_count]
    exits = () if band in _EXITS_HIDDEN_BANDS else perception.exits
    return replace(perception, entities=entities, exits=exits)


# --------------------------------------------------------------------------------------
# Prompt fragments
# --------------------------------------------------------------------------------------


def fog_fragments(world: World, character: Entity) -> list[str]:
    """A single line describing the fog in the character's room, for any viewer there."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None or not room.has_component(FogComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, room, room=room)
    return list(room.get_component(FogComponent).prompt_fragments(ctx))


__all__ = [
    "CLEAR",
    "DARK_LIGHT_THRESHOLD",
    "FOG",
    "HAZE",
    "MAX_DENSITY",
    "THICK",
    "THICKEN_DARK",
    "THICKEN_PER_STRENGTH",
    "THIN_PER_TICK",
    "FogChangedEvent",
    "FogComponent",
    "FogConsequence",
    "fog_band",
    "fog_fragments",
    "perceive_through_fog",
]
