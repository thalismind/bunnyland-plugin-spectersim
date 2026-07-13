from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext
from conftest import execute_handler

from bunnyland_spectersim import GhostDetectorComponent, spawn_ghost_detector
from bunnyland_spectersim.commands import PowerDetectorHandler, SetDetectorVolumeHandler


def _world_with_holder():
    actor = WorldActor()
    room = spawn_entity(actor.world, [RoomComponent(title="Attic")])
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    return actor, room, holder


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=0)


def test_power_off_a_held_detector():
    actor, _room, holder = _world_with_holder()
    detector = spawn_ghost_detector(actor.world)
    _hold(holder, detector)

    result = execute_handler(
        PowerDetectorHandler(),
        _ctx(actor),
        _cmd(holder.id, "power-detector", {"item_id": str(detector.id), "on": False}),
    )

    assert result.ok
    assert detector.get_component(GhostDetectorComponent).powered is False


def test_power_toggles_when_on_is_omitted():
    actor, _room, holder = _world_with_holder()
    detector = spawn_ghost_detector(actor.world)  # powered on by default
    _hold(holder, detector)

    execute_handler(
        PowerDetectorHandler(),
        _ctx(actor),
        _cmd(holder.id, "power-detector", {"item_id": str(detector.id)}),
    )

    assert detector.get_component(GhostDetectorComponent).powered is False


def test_set_volume_updates_gain():
    actor, _room, holder = _world_with_holder()
    detector = spawn_ghost_detector(actor.world)
    _hold(holder, detector)

    result = execute_handler(
        SetDetectorVolumeHandler(),
        _ctx(actor),
        _cmd(holder.id, "set-detector-volume", {"item_id": str(detector.id), "level": 0.25}),
    )

    assert result.ok
    assert detector.get_component(GhostDetectorComponent).gain == 0.25


def test_power_rejects_invalid_character_id():
    actor, _room, holder = _world_with_holder()
    detector = spawn_ghost_detector(actor.world)
    _hold(holder, detector)

    result = execute_handler(
        PowerDetectorHandler(),
        _ctx(actor),
        _cmd("???", "power-detector", {"item_id": str(detector.id)}),
    )

    assert not result.ok
    assert result.reason == "invalid character id"


def test_power_rejects_missing_item():
    actor, _room, holder = _world_with_holder()

    result = execute_handler(
        PowerDetectorHandler(),
        _ctx(actor),
        _cmd(holder.id, "power-detector", {"item_id": "entity_9999"}),
    )

    assert not result.ok
    assert result.reason == "item does not exist"


def test_power_rejects_detector_not_held():
    actor, room, holder = _world_with_holder()
    detector = spawn_ghost_detector(actor.world, room_id=room.id)  # on the floor, not held

    result = execute_handler(
        PowerDetectorHandler(),
        _ctx(actor),
        _cmd(holder.id, "power-detector", {"item_id": str(detector.id)}),
    )

    assert not result.ok
    assert result.reason == "you are not holding that detector"


def test_power_rejects_non_detector_item():
    actor, _room, holder = _world_with_holder()
    lantern = spawn_entity(
        actor.world,
        [IdentityComponent(name="lantern", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(holder, lantern)

    result = execute_handler(
        PowerDetectorHandler(),
        _ctx(actor),
        _cmd(holder.id, "power-detector", {"item_id": str(lantern.id)}),
    )

    assert not result.ok
    assert result.reason == "that is not a detector"


def test_set_volume_rejects_out_of_range():
    actor, _room, holder = _world_with_holder()
    detector = spawn_ghost_detector(actor.world)
    _hold(holder, detector)

    result = execute_handler(
        SetDetectorVolumeHandler(),
        _ctx(actor),
        _cmd(holder.id, "set-detector-volume", {"item_id": str(detector.id), "level": 2.0}),
    )

    assert not result.ok
    assert result.reason == "volume must be between 0 and 1"


def test_set_volume_rejects_non_numeric_level():
    actor, _room, holder = _world_with_holder()
    detector = spawn_ghost_detector(actor.world)
    _hold(holder, detector)

    result = execute_handler(
        SetDetectorVolumeHandler(),
        _ctx(actor),
        _cmd(holder.id, "set-detector-volume", {"item_id": str(detector.id), "level": "loud"}),
    )

    assert not result.ok
    assert result.reason == "volume level must be a number"
