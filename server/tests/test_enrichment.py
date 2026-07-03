from __future__ import annotations

import asyncio

from bunnyland.core import (
    CharacterComponent,
    IdentityComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import CharacterGeneratedEvent, ObjectGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_spectersim import RadioSourceMarkerComponent, SpectralMarkerComponent


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_spectersim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _character(actor, *, tags=(), description=""):
    entity = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    event = CharacterGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="npc",
        entity_kind="character",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        character_key="npc",
        room_id="room_1",
    )
    _publish(actor, event)
    return entity


def test_hostile_character_gets_spectral_marker():
    actor = _actor()
    enemy = _character(actor, tags=("monster", "hostile"))
    assert enemy.has_component(SpectralMarkerComponent)


def test_hostile_detected_from_description_text():
    actor = _actor()
    enemy = _character(actor, description="a shambling undead horror")
    assert enemy.has_component(SpectralMarkerComponent)


def test_benign_character_is_not_marked():
    actor = _actor()
    villager = _character(actor, tags=("farmer", "friendly"), description="a cheerful baker")
    assert not villager.has_component(SpectralMarkerComponent)


def test_broadcast_object_gets_radio_marker():
    actor = _actor()
    entity = spawn_entity(actor.world, [IdentityComponent(name="tower", kind="item")])
    event = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="tower",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=("radio", "transmitter")),
        object_key="tower",
    )
    _publish(actor, event)
    assert entity.has_component(RadioSourceMarkerComponent)


def test_plain_object_is_not_marked():
    actor = _actor()
    entity = spawn_entity(actor.world, [IdentityComponent(name="crate", kind="item")])
    event = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="crate",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=("wooden", "storage")),
        object_key="crate",
    )
    _publish(actor, event)
    assert not entity.has_component(RadioSourceMarkerComponent)
