"""World-generation enrichment: tag generated enemies and broadcasters with markers.

Generated entities expose semantic ``tags``/``wants``/``needs`` and an intent
``description``. This hook scans that text and attaches the detectable marker so detectors
have something to react to in generated worlds — without the core generator knowing this
plugin exists.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import (
    CharacterGeneratedEvent,
    GeneratedEntityEvent,
    ObjectGeneratedEvent,
)
from bunnyland.core.world_actor import WorldActor

from .components import RadioSourceMarkerComponent, SpectralMarkerComponent

#: Words that mark a generated character as something ghost gear should register.
HOSTILE_TERMS = (
    "hostile",
    "enemy",
    "monster",
    "monstrous",
    "ghost",
    "ghostly",
    "spirit",
    "specter",
    "spectre",
    "spectral",
    "wraith",
    "phantom",
    "haunt",
    "undead",
    "zombie",
    "demon",
    "predator",
    "threat",
    "aggressive",
    "kaiju",
)

#: Words that mark a generated object as a radio source.
BROADCAST_TERMS = (
    "radio",
    "transmitter",
    "transmit",
    "beacon",
    "broadcast",
    "antenna",
    "signal",
    "receiver",
    "transceiver",
)


def _text(event: GeneratedEntityEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.entity_kind,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def _mentions(event: GeneratedEntityEvent, terms: tuple[str, ...]) -> bool:
    text = _text(event)
    return any(term in text for term in terms)


class SpecterWorldgenHook:
    """Attach detectable markers to generated enemies and broadcasters."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(CharacterGeneratedEvent, self._on_character)
        actor.bus.subscribe(ObjectGeneratedEvent, self._on_object)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _on_character(self, event: CharacterGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(SpectralMarkerComponent):
            return
        if _mentions(event, HOSTILE_TERMS):
            replace_component(entity, SpectralMarkerComponent())

    def _on_object(self, event: ObjectGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None:
            return
        if not entity.has_component(RadioSourceMarkerComponent) and _mentions(
            event, BROADCAST_TERMS
        ):
            replace_component(entity, RadioSourceMarkerComponent())


__all__ = ["BROADCAST_TERMS", "HOSTILE_TERMS", "SpecterWorldgenHook"]
