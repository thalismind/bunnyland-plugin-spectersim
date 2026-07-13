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

from bunnyland_spectersim import (
    DrawWardHandler,
    PerformRitualHandler,
    PresenceBanishedEvent,
    PresenceWeakenedEvent,
    SpectralMarkerComponent,
    WardComponent,
    WardConsequence,
    WardDrawnEvent,
    ritual_fragments,
    spawn_ritual_kit,
    spawn_ward,
)

EPOCH = 100


def _room(world, *, title="Chapel"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _ghost(world, room, *, strength=1.0):
    ghost = spawn_entity(
        world,
        [
            IdentityComponent(name="ghast", kind="character"),
            SpectralMarkerComponent(strength=strength),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), ghost.id)
    return ghost


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
    return HandlerContext(world=actor.world, epoch=EPOCH)


# =======================================================================================
# WardConsequence
# =======================================================================================


def test_ward_on_room_weakens_a_presence():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(WardComponent(strength=1.0))
    ghost = _ghost(actor.world, room, strength=1.0)

    events = WardConsequence().process(actor.world, EPOCH)

    assert ghost.get_component(SpectralMarkerComponent).strength < 1.0
    assert len(events) == 1
    assert isinstance(events[0], PresenceWeakenedEvent)


def test_placed_ward_entity_warded_room_weakens_presence():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_ward(actor.world, room_id=room.id, strength=1.0)
    ghost = _ghost(actor.world, room, strength=1.0)

    WardConsequence().process(actor.world, EPOCH)

    assert ghost.get_component(SpectralMarkerComponent).strength < 1.0


def test_ward_banishes_a_spent_presence():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(WardComponent(strength=1.0))
    ghost = _ghost(actor.world, room, strength=0.1)

    events = WardConsequence().process(actor.world, EPOCH)

    assert not ghost.has_component(SpectralMarkerComponent)
    assert isinstance(events[0], PresenceBanishedEvent)
    assert events[0].target_id == str(ghost.id)


def test_ward_banishes_after_repeated_ticks():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(WardComponent(strength=1.0))
    ghost = _ghost(actor.world, room, strength=1.0)
    consequence = WardConsequence()

    for tick in range(100):
        consequence.process(actor.world, EPOCH + tick)
        if not ghost.has_component(SpectralMarkerComponent):
            break

    assert not ghost.has_component(SpectralMarkerComponent)


def test_no_wards_means_no_work():
    actor = WorldActor()
    room = _room(actor.world)
    ghost = _ghost(actor.world, room, strength=1.0)

    assert WardConsequence().process(actor.world, EPOCH) == []
    assert ghost.get_component(SpectralMarkerComponent).strength == 1.0


def test_presence_outside_warded_room_is_untouched():
    actor = WorldActor()
    warded = _room(actor.world, title="Chapel")
    warded.add_component(WardComponent(strength=1.0))
    other = _room(actor.world, title="Hall")
    ghost = _ghost(actor.world, other, strength=1.0)

    WardConsequence().process(actor.world, EPOCH)

    assert ghost.get_component(SpectralMarkerComponent).strength == 1.0


# =======================================================================================
# draw-ward
# =======================================================================================


def test_draw_ward_places_ward_on_current_room():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)

    result = execute_handler(DrawWardHandler(), _ctx(actor), _cmd(caster.id, "draw-ward", {}))

    assert result.ok
    assert room.has_component(WardComponent)
    assert isinstance(result.events[0], WardDrawnEvent)
    assert result.events[0].room_id_warded == str(room.id)


def test_draw_ward_consumes_a_held_reagent():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    reagent = spawn_entity(
        actor.world, [IdentityComponent(name="salt", kind="item"), PortableComponent()]
    )
    _hold(caster, reagent)

    result = execute_handler(
        DrawWardHandler(),
        _ctx(actor),
        _cmd(caster.id, "draw-ward", {"reagent_id": str(reagent.id)}),
    )

    assert result.ok
    assert not actor.world.has_entity(reagent.id)


def test_draw_ward_rejects_invalid_character():
    actor = WorldActor()
    result = execute_handler(DrawWardHandler(), _ctx(actor), _cmd("???", "draw-ward", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_draw_ward_rejects_missing_character():
    actor = WorldActor()
    result = execute_handler(DrawWardHandler(), _ctx(actor), _cmd("entity_9999", "draw-ward", {}))
    assert not result.ok
    assert result.reason == "character does not exist"


def test_draw_ward_rejects_character_without_a_room():
    actor = WorldActor()
    caster = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    result = execute_handler(DrawWardHandler(), _ctx(actor), _cmd(caster.id, "draw-ward", {}))
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_draw_ward_rejects_already_warded_room():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(WardComponent())
    caster = _character(actor.world, room)

    result = execute_handler(DrawWardHandler(), _ctx(actor), _cmd(caster.id, "draw-ward", {}))

    assert not result.ok
    assert result.reason == "this room is already warded"


def test_draw_ward_rejects_invalid_reagent():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    result = execute_handler(
        DrawWardHandler(), _ctx(actor), _cmd(caster.id, "draw-ward", {"reagent_id": "???"})
    )
    assert not result.ok
    assert result.reason == "invalid reagent id"


def test_draw_ward_rejects_missing_reagent():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    result = execute_handler(
        DrawWardHandler(), _ctx(actor), _cmd(caster.id, "draw-ward", {"reagent_id": "entity_9999"})
    )
    assert not result.ok
    assert result.reason == "reagent does not exist"


def test_draw_ward_rejects_unheld_reagent():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    reagent = spawn_entity(
        actor.world, [IdentityComponent(name="salt", kind="item"), PortableComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), reagent.id)  # on the floor

    result = execute_handler(
        DrawWardHandler(),
        _ctx(actor),
        _cmd(caster.id, "draw-ward", {"reagent_id": str(reagent.id)}),
    )

    assert not result.ok
    assert result.reason == "you are not holding that reagent"


# =======================================================================================
# perform-ritual
# =======================================================================================


def test_perform_ritual_weakens_a_presence():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world, potency=0.5)
    _hold(caster, kit)
    ghost = _ghost(actor.world, room, strength=1.0)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id)}),
    )

    assert result.ok
    assert isinstance(result.events[0], PresenceWeakenedEvent)
    assert ghost.get_component(SpectralMarkerComponent).strength == 0.5


def test_perform_ritual_banishes_a_weak_presence():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world, potency=1.0)
    _hold(caster, kit)
    ghost = _ghost(actor.world, room, strength=0.5)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id)}),
    )

    assert result.ok
    assert isinstance(result.events[0], PresenceBanishedEvent)
    assert not ghost.has_component(SpectralMarkerComponent)


def test_perform_ritual_targets_named_presence():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world, potency=1.0)
    _hold(caster, kit)
    _ghost(actor.world, room, strength=1.0)
    chosen = _ghost(actor.world, room, strength=0.4)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id), "target_id": str(chosen.id)}),
    )

    assert result.ok
    assert not chosen.has_component(SpectralMarkerComponent)


def test_perform_ritual_rejects_invalid_character():
    actor = WorldActor()
    result = execute_handler(
        PerformRitualHandler(), _ctx(actor), _cmd("???", "perform-ritual", {"kit_id": "entity_1"})
    )
    assert not result.ok
    assert result.reason == "invalid character id"


def test_perform_ritual_rejects_invalid_kit_id():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    result = execute_handler(
        PerformRitualHandler(), _ctx(actor), _cmd(caster.id, "perform-ritual", {"kit_id": "???"})
    )
    assert not result.ok
    assert result.reason == "invalid kit id"


def test_perform_ritual_rejects_missing_kit():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": "entity_9999"}),
    )
    assert not result.ok
    assert result.reason == "ritual kit does not exist"


def test_perform_ritual_rejects_unheld_kit():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world, room_id=room.id)  # on the floor

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id)}),
    )

    assert not result.ok
    assert result.reason == "you are not holding that ritual kit"


def test_perform_ritual_rejects_non_kit_item():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    lantern = spawn_entity(
        actor.world,
        [IdentityComponent(name="lantern", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(caster, lantern)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(lantern.id)}),
    )

    assert not result.ok
    assert result.reason == "that is not a ritual kit"


def test_perform_ritual_rejects_caster_without_a_room():
    actor = WorldActor()
    caster = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    kit = spawn_ritual_kit(actor.world)
    _hold(caster, kit)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id)}),
    )

    assert not result.ok
    assert result.reason == "you are not in a room"


def test_perform_ritual_rejects_when_nothing_to_banish():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world)
    _hold(caster, kit)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id)}),
    )

    assert not result.ok
    assert result.reason == "there is nothing to banish here"


def test_perform_ritual_rejects_target_in_another_room():
    actor = WorldActor()
    room = _room(actor.world)
    other = _room(actor.world, title="Hall")
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world)
    _hold(caster, kit)
    elsewhere = _ghost(actor.world, other, strength=1.0)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id), "target_id": str(elsewhere.id)}),
    )

    assert not result.ok
    assert result.reason == "target is not here"


def test_perform_ritual_rejects_non_spectral_target():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world)
    _hold(caster, kit)
    bystander = _character(actor.world, room, name="Kell")

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id), "target_id": str(bystander.id)}),
    )

    assert not result.ok
    assert result.reason == "target is not a spectral presence"


def test_perform_ritual_rejects_missing_target():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world)
    _hold(caster, kit)

    result = execute_handler(
        PerformRitualHandler(),
        _ctx(actor),
        _cmd(caster.id, "perform-ritual", {"kit_id": str(kit.id), "target_id": "entity_9999"}),
    )

    assert not result.ok
    assert result.reason == "target does not exist"


# =======================================================================================
# prompt fragments
# =======================================================================================


def test_ward_fragment_shows_room_protection():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(WardComponent())
    character = _character(actor.world, room)

    lines = ritual_fragments(actor.world, character)

    assert lines == ["A ward here holds the space against spectral presences."]


def test_ward_fragment_shows_placed_ward_entity():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_ward(actor.world, room_id=room.id)
    character = _character(actor.world, room)

    lines = ritual_fragments(actor.world, character)

    assert "A ward here holds the space against spectral presences." in lines


def test_ritual_kit_fragment_is_first_person_for_holder():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    kit = spawn_ritual_kit(actor.world)
    _hold(character, kit)

    lines = ritual_fragments(actor.world, character)

    assert "You carry a ritual kit ready to banish a presence." in lines


def test_no_ritual_fragments_in_a_plain_room():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)

    assert ritual_fragments(actor.world, character) == []


def test_ritual_fragments_empty_for_none_character():
    actor = WorldActor()
    assert ritual_fragments(actor.world, None) == []
