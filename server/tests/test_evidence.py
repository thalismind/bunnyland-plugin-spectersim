from __future__ import annotations

from dataclasses import replace

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
from bunnyland.core.ecs import replace_component
from bunnyland.core.handlers import HandlerContext
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

from bunnyland_spectersim import (
    EvidenceComponent,
    EvidenceEntry,
    EvidenceLogComponent,
    EvidenceRecordedEvent,
    GhostDetectorComponent,
    LogReadingHandler,
    SpectralMarkerComponent,
    evidence_fragments,
    spawn_ghost_detector,
    spawn_recorder,
)

EPOCH = 100


def _room(world, *, title="Wing"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _ghost(world, room, *, strength=1.0, name="ghast"):
    ghost = spawn_entity(
        world,
        [
            IdentityComponent(name=name, kind="character"),
            SpectralMarkerComponent(strength=strength),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), ghost.id)
    return ghost


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _set_detector(detector, **fields):
    replace_component(detector, replace(detector.get_component(GhostDetectorComponent), **fields))


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="log-reading",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def _log(character):
    return character.get_component(EvidenceLogComponent).entries


# =======================================================================================
# happy paths
# =======================================================================================


def test_bare_handed_investigator_records_a_presence():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    _ghost(actor.world, room)

    result = LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))

    assert result.ok
    assert isinstance(result.events[0], EvidenceRecordedEvent)
    assert result.events[0].count == 1
    assert len(_log(investigator)) == 1


def test_recorder_captures_evidence():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    recorder = spawn_recorder(actor.world)
    _hold(investigator, recorder)
    _ghost(actor.world, room)

    result = LogReadingHandler().execute(
        _ctx(actor), _cmd(investigator.id, {"recorder_id": str(recorder.id)})
    )

    assert result.ok
    assert len(_log(investigator)) == 1


def test_reacting_detector_alone_yields_a_spike():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    _set_detector(detector, volume=2.5)  # NEAR band, no presence in the room

    result = LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))

    assert result.ok
    assert [entry.kind for entry in _log(investigator)] == ["detector spike"]


def test_held_reacting_detector_counts_as_evidence():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    detector = spawn_ghost_detector(actor.world)
    _hold(investigator, detector)
    _set_detector(detector, volume=3.5)

    result = LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))

    assert result.ok
    assert "detector spike" in [entry.kind for entry in _log(investigator)]


def test_presence_and_spike_both_recorded():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    _ghost(actor.world, room)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    _set_detector(detector, volume=5.0)

    result = LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))

    assert result.ok
    assert result.events[0].count == 2


def test_readings_accumulate_across_invocations():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    _ghost(actor.world, room)

    LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))
    LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))

    assert len(_log(investigator)) == 2


def test_evidence_content_is_deterministic():
    def run():
        actor = WorldActor()
        room = _room(actor.world)
        investigator = _character(actor.world, room)
        ghost = _ghost(actor.world, room)
        # Pin the ghost id so both runs derive from the same stable id.
        LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))
        return _log(investigator)[0], str(ghost.id)

    first, first_id = run()
    second, second_id = run()
    assert first_id == second_id
    assert first.kind == second.kind
    assert first.text == second.text


def test_powered_off_detector_is_not_evidence():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    _set_detector(detector, powered=False, volume=0.0)

    result = LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))

    assert not result.ok
    assert result.reason == "there is nothing to record here"


# =======================================================================================
# rejection paths (invalid -> missing -> not-held -> wrong-kind -> invalid-state)
# =======================================================================================


def test_rejects_invalid_character():
    actor = WorldActor()
    result = LogReadingHandler().execute(_ctx(actor), _cmd("???", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_rejects_missing_character():
    actor = WorldActor()
    result = LogReadingHandler().execute(_ctx(actor), _cmd("entity_9999", {}))
    assert not result.ok
    assert result.reason == "character does not exist"


def test_rejects_invalid_recorder_id():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    result = LogReadingHandler().execute(
        _ctx(actor), _cmd(investigator.id, {"recorder_id": "???"})
    )
    assert not result.ok
    assert result.reason == "invalid recorder id"


def test_rejects_missing_recorder():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    result = LogReadingHandler().execute(
        _ctx(actor), _cmd(investigator.id, {"recorder_id": "entity_9999"})
    )
    assert not result.ok
    assert result.reason == "recorder does not exist"


def test_rejects_unheld_recorder():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    recorder = spawn_recorder(actor.world, room_id=room.id)  # on the floor
    result = LogReadingHandler().execute(
        _ctx(actor), _cmd(investigator.id, {"recorder_id": str(recorder.id)})
    )
    assert not result.ok
    assert result.reason == "you are not holding that recorder"


def test_rejects_non_recorder_item():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    lantern = spawn_entity(
        actor.world,
        [IdentityComponent(name="lantern", kind="item"), PortableComponent(), HoldableComponent()],
    )
    _hold(investigator, lantern)
    result = LogReadingHandler().execute(
        _ctx(actor), _cmd(investigator.id, {"recorder_id": str(lantern.id)})
    )
    assert not result.ok
    assert result.reason == "that is not a recorder"


def test_rejects_investigator_without_a_room():
    actor = WorldActor()
    recorder = spawn_recorder(actor.world)
    investigator = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    _hold(investigator, recorder)
    result = LogReadingHandler().execute(
        _ctx(actor), _cmd(investigator.id, {"recorder_id": str(recorder.id)})
    )
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_rejects_when_nothing_to_record():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    result = LogReadingHandler().execute(_ctx(actor), _cmd(investigator.id, {}))
    assert not result.ok
    assert result.reason == "there is nothing to record here"


# =======================================================================================
# prompt fragments
# =======================================================================================


def test_log_summary_counts_by_kind():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    replace_component(
        investigator,
        EvidenceLogComponent(
            entries=(
                EvidenceEntry(kind="EVP capture", text="a"),
                EvidenceEntry(kind="EVP capture", text="b"),
                EvidenceEntry(kind="cold spot", text="c"),
            )
        ),
    )

    lines = evidence_fragments(actor.world, investigator)

    assert lines == ["Your evidence log holds 2 EVP captures, 1 cold spot."]


def test_recorder_fragment_is_first_person_for_holder():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    recorder = spawn_recorder(actor.world)
    _hold(investigator, recorder)

    lines = evidence_fragments(actor.world, investigator)

    assert "You carry an EVP recorder ready to capture evidence." in lines


def test_no_evidence_fragments_without_a_log_or_recorder():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)

    assert evidence_fragments(actor.world, investigator) == []


def test_evidence_fragments_empty_for_none_character():
    actor = WorldActor()
    assert evidence_fragments(actor.world, None) == []


def test_empty_log_produces_no_line():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    replace_component(investigator, EvidenceLogComponent())

    assert evidence_fragments(actor.world, investigator) == []


def test_log_is_private_to_its_owner():
    actor = WorldActor()
    room = _room(actor.world)
    investigator = _character(actor.world, room)
    other = _character(actor.world, room, name="Kell")
    replace_component(
        investigator,
        EvidenceLogComponent(entries=(EvidenceEntry(kind="EVP capture", text="a"),)),
    )

    ctx = ComponentPromptContext.for_entity(
        actor.world, investigator, perspective=PromptPerspective(viewer=other), room=room
    )
    assert investigator.get_component(EvidenceLogComponent).prompt_fragments(ctx) == ()


def test_recorder_not_first_person_for_bystander():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    other = _character(actor.world, room, name="Kell")
    recorder = spawn_recorder(actor.world)
    _hold(holder, recorder)

    ctx = ComponentPromptContext.for_entity(
        actor.world, recorder, perspective=PromptPerspective(viewer=other), room=room
    )
    assert recorder.get_component(EvidenceComponent).prompt_fragments(ctx) == ()
