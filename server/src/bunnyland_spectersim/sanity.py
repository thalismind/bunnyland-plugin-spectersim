"""Sanity: a dread meter that erodes near spectral presences and in the dark.

Sanity is the inverse of the ``needs`` meters — a *high* value is good (calm) and a *low*
value is bad (dread) — so it carries its own ``current``/``maximum`` fields rather than the
shared rising :class:`~bunnyland.mechanics.meter.Meter`. A per-tick
:class:`SanityConsequence` drains it for every active character standing near
:class:`~bunnyland_spectersim.components.SpectralMarkerComponent` entities or in a dark room,
and lets it recover in a safe or bright, spirit-free room.

At low sanity the character's *own* prompt gains escalating distortion lines; those are
first-person only (viewer == the character), so only the affected player/agent reads them.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    DeadComponent,
    LightComponent,
    RoomComponent,
    SuspendedComponent,
)
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, World

from .components import SpectralMarkerComponent
from .spatial import room_of

# --------------------------------------------------------------------------------------
# Tuning
# --------------------------------------------------------------------------------------

#: A room dimmer than this (0..1) counts as dark and unsettling.
DARK_LIGHT_THRESHOLD = 0.3

#: Sanity lost per tick, per unit of same-room spectral marker strength.
DRAIN_PER_STRENGTH = 6.0
#: Extra sanity lost per tick while standing in the dark.
DARK_DRAIN = 4.0
#: Sanity regained per tick in a safe room with no spectral presence.
SAFE_RECOVER = 5.0
#: Sanity regained per tick in a bright, spirit-free (but not explicitly safe) room.
BRIGHT_RECOVER = 3.0

# Band edges, as a fraction of ``maximum`` (a high fraction is calm).
STABLE = "stable"
SHAKEN = "shaken"
FRAYED = "frayed"
CRITICAL = "critical"
SHAKEN_AT = 0.6
FRAYED_AT = 0.35
CRITICAL_AT = 0.15

# Escalating first-person distortion lines, cumulative as sanity worsens.
_SHAKEN_LINE = "Your hands won't stop shaking."
_FRAYED_LINE = "You hear whispering that isn't there."
_CRITICAL_LINE = "Something is standing just behind you; you can feel its breath on your neck."


def sanity_band(component: SanityComponent) -> str:
    """Coarse dread band for a sanity component (``stable`` is best)."""
    fraction = component.current / component.maximum if component.maximum > 0 else 0.0
    if fraction >= SHAKEN_AT:
        return STABLE
    if fraction >= FRAYED_AT:
        return SHAKEN
    if fraction >= CRITICAL_AT:
        return FRAYED
    return CRITICAL


def _distortion_lines(band: str) -> tuple[str, ...]:
    if band == SHAKEN:
        return (_SHAKEN_LINE,)
    if band == FRAYED:
        return (_SHAKEN_LINE, _FRAYED_LINE)
    if band == CRITICAL:
        return (_SHAKEN_LINE, _FRAYED_LINE, _CRITICAL_LINE)
    return ()


@dataclass(frozen=True)
class SanityComponent(Component):
    """A character's dread meter. ``current`` falls toward 0 under supernatural stress."""

    current: float = 100.0
    maximum: float = 100.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        # Only the character themselves feels their own dread.
        if not ctx.is_first_person:
            return ()
        return _distortion_lines(sanity_band(self))


class SanityChangedEvent(DomainEvent):
    """A character's sanity crossed into a new dread band."""

    value: float
    band: str


class SanityConsequence:
    """Drain/recover every active character's sanity from their surroundings each tick."""

    def __init__(
        self,
        *,
        drain_per_strength: float = DRAIN_PER_STRENGTH,
        dark_drain: float = DARK_DRAIN,
        safe_recover: float = SAFE_RECOVER,
        bright_recover: float = BRIGHT_RECOVER,
        dark_threshold: float = DARK_LIGHT_THRESHOLD,
    ):
        self.drain_per_strength = drain_per_strength
        self.dark_drain = dark_drain
        self.safe_recover = safe_recover
        self.bright_recover = bright_recover
        self.dark_threshold = dark_threshold

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        strength_by_room = self._spectral_strength_by_room(world)
        events: list[DomainEvent] = []
        for character in list(world.query().with_all([SanityComponent]).execute_entities()):
            # Harmful world participation excludes suspended and dead characters (spec 8.1).
            if character.has_component(SuspendedComponent) or character.has_component(
                DeadComponent
            ):
                continue
            event = self._update_character(world, epoch, character, strength_by_room)
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

    def _update_character(self, world, epoch, character, strength_by_room):
        room = room_of(world, character.id)
        if room is None:
            return None
        strength = strength_by_room.get(str(room.id), 0.0)
        dark = self._is_dark(room)
        safe = _room_is_safe(room)

        delta = 0.0
        if strength > 0.0:
            delta -= self.drain_per_strength * strength
        if dark:
            delta -= self.dark_drain
        if delta == 0.0:
            # No stressors: recover in a safe room, or a bright spirit-free one.
            if safe:
                delta = self.safe_recover
            elif not dark:
                delta = self.bright_recover

        component = character.get_component(SanityComponent)
        new_current = max(0.0, min(component.maximum, component.current + delta))
        if new_current == component.current:
            return None
        old_band = sanity_band(component)
        updated = replace(component, current=new_current)
        replace_component(character, updated)
        new_band = sanity_band(updated)
        if new_band == old_band:
            return None
        return SanityChangedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PRIVATE,
                actor_id=str(character.id),
                value=new_current,
                band=new_band,
            )
        )

    def _is_dark(self, room) -> bool:
        if not room.has_component(LightComponent):
            return False
        light = room.get_component(LightComponent)
        level = light.level if light.enabled else 0.0
        return level < self.dark_threshold


def _room_is_safe(room) -> bool:
    return room.has_component(RoomComponent) and room.get_component(RoomComponent).safe


def sanity_fragments(world: World, character) -> list[str]:
    """First-person dread distortion lines for a character's own prompt."""
    if character is None or not character.has_component(SanityComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return list(character.get_component(SanityComponent).prompt_fragments(ctx))


__all__ = [
    "BRIGHT_RECOVER",
    "CRITICAL",
    "DARK_DRAIN",
    "DARK_LIGHT_THRESHOLD",
    "DRAIN_PER_STRENGTH",
    "FRAYED",
    "SAFE_RECOVER",
    "SHAKEN",
    "STABLE",
    "SanityChangedEvent",
    "SanityComponent",
    "SanityConsequence",
    "sanity_band",
    "sanity_fragments",
]
