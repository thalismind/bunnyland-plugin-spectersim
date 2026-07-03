from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    DeadComponent,
    IdentityComponent,
    LightComponent,
    RoomComponent,
    SuspendedComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_spectersim import (
    SanityChangedEvent,
    SanityComponent,
    SanityConsequence,
    SpectralMarkerComponent,
    sanity_band,
    sanity_fragments,
)

EPOCH = 100


def _room(world, *, title="Cellar", safe=False, light=None):
    components = [RoomComponent(title=title, safe=safe)]
    if light is not None:
        components.append(LightComponent(level=light))
    return spawn_entity(world, components)


def _character(world, room, *, current=100.0, maximum=100.0):
    character = spawn_entity(
        world,
        [
            IdentityComponent(name="Vin", kind="character"),
            CharacterComponent(),
            SanityComponent(current=current, maximum=maximum),
        ],
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


def _current(character):
    return character.get_component(SanityComponent).current


# -- band classification ----------------------------------------------------------------


def test_sanity_bands_by_fraction():
    assert sanity_band(SanityComponent(current=100.0)) == "stable"
    assert sanity_band(SanityComponent(current=50.0)) == "shaken"
    assert sanity_band(SanityComponent(current=25.0)) == "frayed"
    assert sanity_band(SanityComponent(current=5.0)) == "critical"


def test_sanity_band_handles_zero_maximum():
    assert sanity_band(SanityComponent(current=0.0, maximum=0.0)) == "critical"


# -- drain ------------------------------------------------------------------------------


def test_spectral_presence_drains_sanity():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    _ghost(actor.world, room, strength=1.0)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) < 100.0


def test_stronger_presence_drains_faster():
    actor = WorldActor()
    faint_room = _room(actor.world)
    strong_room = _room(actor.world)
    faint_victim = _character(actor.world, faint_room)
    strong_victim = _character(actor.world, strong_room)
    _ghost(actor.world, faint_room, strength=1.0)
    _ghost(actor.world, strong_room, strength=3.0)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(strong_victim) < _current(faint_victim)


def test_darkness_alone_drains_sanity():
    actor = WorldActor()
    room = _room(actor.world, safe=False, light=0.05)
    character = _character(actor.world, room)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) < 100.0


def test_sanity_clamps_at_zero():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, current=1.0)
    _ghost(actor.world, room, strength=5.0)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) == 0.0


# -- recovery ---------------------------------------------------------------------------


def test_safe_room_recovers_sanity():
    actor = WorldActor()
    room = _room(actor.world, safe=True, light=1.0)
    character = _character(actor.world, room, current=50.0)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) > 50.0


def test_bright_unsafe_room_recovers_less_than_safe():
    actor = WorldActor()
    safe_room = _room(actor.world, safe=True, light=1.0)
    bright_room = _room(actor.world, safe=False, light=1.0)
    safe_victim = _character(actor.world, safe_room, current=50.0)
    bright_victim = _character(actor.world, bright_room, current=50.0)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(safe_victim) > _current(bright_victim) > 50.0


def test_recovery_clamps_at_maximum():
    actor = WorldActor()
    room = _room(actor.world, safe=True)
    character = _character(actor.world, room, current=99.0)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) == 100.0


def test_dark_unsafe_room_with_no_presence_does_not_recover():
    actor = WorldActor()
    room = _room(actor.world, safe=False, light=0.05)
    character = _character(actor.world, room, current=50.0)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) < 50.0


# -- excluded characters ----------------------------------------------------------------


def test_suspended_character_is_skipped():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    character.add_component(SuspendedComponent())
    _ghost(actor.world, room)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) == 100.0


def test_dead_character_is_skipped():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    character.add_component(DeadComponent(died_at_epoch=EPOCH, cause="fright"))
    _ghost(actor.world, room)

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) == 100.0


def test_character_without_a_room_is_skipped():
    actor = WorldActor()
    character = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="drifter", kind="character"),
            CharacterComponent(),
            SanityComponent(),
        ],
    )

    assert SanityConsequence().process(actor.world, EPOCH) == []
    assert _current(character) == 100.0


def test_marker_without_a_room_is_ignored():
    actor = WorldActor()
    room = _room(actor.world, safe=True)
    character = _character(actor.world, room, current=50.0)
    spawn_entity(actor.world, [SpectralMarkerComponent()])  # loose, no room

    SanityConsequence().process(actor.world, EPOCH)

    assert _current(character) > 50.0  # unaffected presence, room recovers


# -- band-crossing events ---------------------------------------------------------------


def test_band_crossing_emits_event():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, current=61.0)
    _ghost(actor.world, room, strength=1.0)  # -6 -> 55, crosses stable->shaken

    events = SanityConsequence().process(actor.world, EPOCH)

    assert len(events) == 1
    assert isinstance(events[0], SanityChangedEvent)
    assert events[0].band == "shaken"
    assert events[0].value == _current(character)


def test_no_event_when_band_unchanged():
    actor = WorldActor()
    room = _room(actor.world)
    _character(actor.world, room, current=100.0)
    _ghost(actor.world, room, strength=1.0)  # 100 -> 94, still stable

    assert SanityConsequence().process(actor.world, EPOCH) == []


def test_no_change_no_event_when_stable_at_maximum_in_safe_room():
    actor = WorldActor()
    room = _room(actor.world, safe=True)
    _character(actor.world, room, current=100.0)  # already full, safe -> no change

    assert SanityConsequence().process(actor.world, EPOCH) == []


# -- prompt fragments -------------------------------------------------------------------


def test_calm_character_has_no_distortion():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, current=100.0)

    assert sanity_fragments(actor.world, character) == []


def test_shaken_character_reads_one_line():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, current=50.0)

    lines = sanity_fragments(actor.world, character)

    assert lines == ["Your hands won't stop shaking."]


def test_frayed_character_hears_whispering():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, current=25.0)

    lines = sanity_fragments(actor.world, character)

    assert "You hear whispering that isn't there." in lines
    assert "Your hands won't stop shaking." in lines


def test_critical_character_hallucinates_a_presence():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, current=5.0)

    lines = sanity_fragments(actor.world, character)

    assert len(lines) == 3
    assert any("standing just behind you" in line for line in lines)


def test_fragments_empty_for_character_without_sanity():
    actor = WorldActor()
    room = _room(actor.world)
    character = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)

    assert sanity_fragments(actor.world, character) == []


def test_fragments_not_shown_to_other_viewers():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room, current=5.0)
    other = _character(actor.world, room, current=100.0)
    # A third-person viewer should not read the afflicted character's private dread.
    from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

    ctx = ComponentPromptContext.for_entity(
        actor.world, character, perspective=PromptPerspective(viewer=other), room=room
    )
    assert character.get_component(SanityComponent).prompt_fragments(ctx) == ()
