"""Spawn factories for detector items.

The loader does not consume ``ContentContribution.prefabs``, so detectors are created with
these ``spawn_entity`` helpers (from tests, admin tooling, or a worldgen hook). Each device
is a portable, holdable item carrying its detector component; pass ``room_id`` to drop it
into a room, or leave it out to spawn it uncontained (e.g. straight into an inventory).
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from relics import Entity, World

from .components import GhostDetectorComponent, RadioDetectorComponent


def _link_into_room(world: World, item: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)


def spawn_ghost_detector(world: World, *, room_id=None, sound: str = "wail") -> Entity:
    """Spawn a ghost detector item, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name="ghost detector", kind="item", tags=("spectersim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            GhostDetectorComponent(sound=sound),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


def spawn_radio(world: World, *, room_id=None, sound: str = "hiss") -> Entity:
    """Spawn a radio item, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name="radio", kind="item", tags=("spectersim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            RadioDetectorComponent(sound=sound),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


__all__ = ["spawn_ghost_detector", "spawn_radio"]
