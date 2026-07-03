from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component

from bunnyland_spectersim import GhostDetectorComponent, spawn_ghost_detector, spectersim_fragments


def _room(world):
    return spawn_entity(world, [RoomComponent(title="Ward")])


def _character(world, room, name):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _set(detector, **fields):
    replace_component(detector, replace(detector.get_component(GhostDetectorComponent), **fields))


def test_holder_reads_first_person_reacting_line():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room, "Vin")
    detector = spawn_ghost_detector(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), detector.id)
    _set(detector, volume=2.5)  # NEAR band

    lines = spectersim_fragments(actor.world, holder)

    assert lines == ["Your ghost detector gives a steady wail — something marked is close."]


def test_bystander_reads_third_person_line_for_floor_device():
    actor = WorldActor()
    room = _room(actor.world)
    bystander = _character(actor.world, room, "Kell")
    detector = spawn_ghost_detector(actor.world, room_id=room.id)  # on the floor
    _set(detector, volume=3.5)  # LOUD band

    lines = spectersim_fragments(actor.world, bystander)

    assert lines == ["A ghost detector here gives a loud wail — something marked is close."]


def test_holder_sees_switched_off_state():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room, "Vin")
    detector = spawn_ghost_detector(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), detector.id)
    _set(detector, powered=False, volume=0.0)

    lines = spectersim_fragments(actor.world, holder)

    assert lines == ["Your ghost detector is switched off."]


def test_silent_floor_device_is_not_described_to_bystanders():
    actor = WorldActor()
    room = _room(actor.world)
    bystander = _character(actor.world, room, "Kell")
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    _set(detector, volume=0.0)  # powered but nothing detected

    assert spectersim_fragments(actor.world, bystander) == []
