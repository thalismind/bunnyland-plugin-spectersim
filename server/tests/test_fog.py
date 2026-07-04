from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    LightComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component
from bunnyland.core.edges import ExitTo
from bunnyland.prompts.context import ComponentPromptContext

from bunnyland_spectersim import (
    FogChangedEvent,
    FogComponent,
    FogConsequence,
    SpectralMarkerComponent,
    fog_band,
    fog_fragments,
    perceive_through_fog,
)

EPOCH = 100


def _room(world, *, title="Marsh", light=None, indoor=False, density=None):
    components = [RoomComponent(title=title, indoor=indoor)]
    if light is not None:
        components.append(LightComponent(level=light))
    if density is not None:
        components.append(FogComponent(density=density))
    return spawn_entity(world, components)


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


def _density(room):
    return room.get_component(FogComponent).density


# =======================================================================================
# band classification
# =======================================================================================


def test_fog_bands_by_density():
    assert fog_band(0.0) == "clear"
    assert fog_band(0.3) == "haze"
    assert fog_band(0.6) == "fog"
    assert fog_band(0.9) == "thick"


# =======================================================================================
# FogConsequence
# =======================================================================================


def test_darkness_thickens_fog():
    actor = WorldActor()
    room = _room(actor.world, light=0.05, density=0.1)

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) > 0.1


def test_spectral_presence_thickens_fog():
    actor = WorldActor()
    room = _room(actor.world, light=1.0, density=0.1)
    _ghost(actor.world, room, strength=2.0)

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) > 0.1


def test_bright_spirit_free_room_thins_fog():
    actor = WorldActor()
    room = _room(actor.world, light=1.0, density=0.5)

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) < 0.5


def test_fog_clamps_at_zero():
    actor = WorldActor()
    room = _room(actor.world, light=1.0, density=0.05)

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) == 0.0


def test_fog_clamps_at_max():
    actor = WorldActor()
    room = _room(actor.world, light=0.05, density=0.95)
    _ghost(actor.world, room, strength=5.0)

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) == 1.0


def test_room_without_light_component_is_not_treated_as_dark():
    actor = WorldActor()
    room = _room(actor.world, density=0.5)  # no LightComponent -> not dark -> thins

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) < 0.5


def test_disabled_light_counts_as_dark():
    actor = WorldActor()
    room = _room(actor.world, density=0.1)
    replace_component(room, LightComponent(level=1.0, enabled=False))

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) > 0.1


def test_no_fog_rooms_means_no_work():
    actor = WorldActor()
    _room(actor.world, light=0.05)  # dark but no FogComponent

    assert FogConsequence().process(actor.world, EPOCH) == []


def test_marker_without_a_room_is_ignored():
    actor = WorldActor()
    room = _room(actor.world, light=1.0, density=0.5)
    spawn_entity(actor.world, [SpectralMarkerComponent()])  # loose, no room

    FogConsequence().process(actor.world, EPOCH)

    assert _density(room) < 0.5  # unattached presence, room still thins


def test_band_crossing_emits_event():
    actor = WorldActor()
    room = _room(actor.world, light=0.05, density=0.18)  # clear, +0.15 -> 0.33 haze

    events = FogConsequence().process(actor.world, EPOCH)

    assert len(events) == 1
    assert isinstance(events[0], FogChangedEvent)
    assert events[0].band == "haze"
    assert events[0].density == _density(room)


def test_no_event_when_band_unchanged():
    actor = WorldActor()
    _room(actor.world, light=0.05, density=0.0)  # clear, +0.15 -> 0.15 still clear

    assert FogConsequence().process(actor.world, EPOCH) == []


def test_no_event_and_no_change_when_already_clear_and_bright():
    actor = WorldActor()
    room = _room(actor.world, light=1.0, density=0.0)  # already clear, thinning stays 0

    assert FogConsequence().process(actor.world, EPOCH) == []
    assert _density(room) == 0.0


# =======================================================================================
# perceive_through_fog
# =======================================================================================


def _add_items(world, room, count):
    for i in range(count):
        item = spawn_entity(world, [IdentityComponent(name=f"box{i}", kind="item")])
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)


def test_clear_room_perceives_everything():
    actor = WorldActor()
    room = _room(actor.world, density=0.0)
    character = _character(actor.world, room)
    _add_items(actor.world, room, 6)

    perception = perceive_through_fog(actor.world, character)

    assert len(perception.entities) == 6


def test_fog_reduces_visible_entities():
    actor = WorldActor()
    room = _room(actor.world, density=0.6)  # FOG band -> keep ~34%
    character = _character(actor.world, room)
    _add_items(actor.world, room, 6)

    perception = perceive_through_fog(actor.world, character)

    assert 0 < len(perception.entities) < 6


def test_thick_fog_hides_everything_and_exits():
    actor = WorldActor()
    room = _room(actor.world, density=0.9)  # THICK band
    other = _room(actor.world, title="Cellar")
    room.add_relationship(ExitTo(direction="north"), other.id)
    character = _character(actor.world, room)
    _add_items(actor.world, room, 4)

    perception = perceive_through_fog(actor.world, character)

    assert perception.entities == ()
    assert perception.exits == ()


def test_fog_hides_exits_but_not_all_entities_in_fog_band():
    actor = WorldActor()
    room = _room(actor.world, density=0.6)  # FOG band
    other = _room(actor.world, title="Cellar")
    room.add_relationship(ExitTo(direction="north"), other.id)
    character = _character(actor.world, room)
    _add_items(actor.world, room, 6)

    perception = perceive_through_fog(actor.world, character)

    assert perception.exits == ()
    assert len(perception.entities) > 0


def test_haze_keeps_exits_visible():
    actor = WorldActor()
    room = _room(actor.world, density=0.3)  # HAZE band
    other = _room(actor.world, title="Cellar")
    room.add_relationship(ExitTo(direction="north"), other.id)
    character = _character(actor.world, room)

    perception = perceive_through_fog(actor.world, character)

    assert len(perception.exits) == 1


def test_no_fog_component_leaves_perception_unchanged():
    actor = WorldActor()
    room = _room(actor.world)  # no FogComponent
    character = _character(actor.world, room)
    _add_items(actor.world, room, 4)

    perception = perceive_through_fog(actor.world, character)

    assert len(perception.entities) == 4


def test_blind_character_still_perceives_nothing_through_fog():
    from bunnyland.core import SuspendedComponent

    actor = WorldActor()
    room = _room(actor.world, density=0.9)
    character = _character(actor.world, room)
    character.add_component(SuspendedComponent())

    perception = perceive_through_fog(actor.world, character)

    assert not perception.can_perceive


# =======================================================================================
# prompt fragments
# =======================================================================================


def test_fog_fragment_describes_thick_fog():
    actor = WorldActor()
    room = _room(actor.world, density=0.9)
    character = _character(actor.world, room)

    lines = fog_fragments(actor.world, character)

    assert lines == ["A thick fog swallows the room; you can barely see."]


def test_fog_fragment_describes_haze():
    actor = WorldActor()
    room = _room(actor.world, density=0.3)
    character = _character(actor.world, room)

    lines = fog_fragments(actor.world, character)

    assert lines == ["A thin haze hangs in the air."]


def test_clear_room_has_no_fog_fragment():
    actor = WorldActor()
    room = _room(actor.world, density=0.05)
    character = _character(actor.world, room)

    assert fog_fragments(actor.world, character) == []


def test_no_fog_component_has_no_fragment():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)

    assert fog_fragments(actor.world, character) == []


def test_fog_fragment_empty_for_none_character():
    actor = WorldActor()
    assert fog_fragments(actor.world, None) == []


def test_fog_component_fragment_is_shown_to_anyone_in_room():
    actor = WorldActor()
    room = _room(actor.world, density=0.6)
    ctx = ComponentPromptContext.for_entity(actor.world, room, room=room)

    lines = room.get_component(FogComponent).prompt_fragments(ctx)

    assert lines == ("Fog fills the room, softening every edge.",)
