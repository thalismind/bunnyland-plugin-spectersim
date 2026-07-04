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
from .evidence import EvidenceComponent
from .rituals import RitualKitComponent, WardComponent


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


def spawn_ritual_kit(world: World, *, room_id=None, potency: float = 0.5) -> Entity:
    """Spawn a holdable ritual kit item, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name="ritual kit", kind="item", tags=("spectersim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            RitualKitComponent(potency=potency),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


def spawn_recorder(world: World, *, room_id=None) -> Entity:
    """Spawn a holdable EVP recorder item, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name="EVP recorder", kind="item", tags=("spectersim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            EvidenceComponent(),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


def spawn_ward(world: World, *, room_id=None, strength: float = 1.0) -> Entity:
    """Spawn a standalone ward entity, optionally placed in ``room_id`` to protect it."""
    ward = spawn_entity(
        world,
        [
            IdentityComponent(name="ward", kind="ward", tags=("spectersim",)),
            WardComponent(strength=strength),
        ],
    )
    _link_into_room(world, ward, room_id)
    return ward


__all__ = [
    "spawn_ghost_detector",
    "spawn_radio",
    "spawn_recorder",
    "spawn_ritual_kit",
    "spawn_ward",
]
