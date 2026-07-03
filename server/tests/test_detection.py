from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    NoiseComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import PerceptionComponent
from bunnyland.core.consequences import HearingConsequence
from bunnyland.core.ecs import replace_component

from bunnyland_spectersim import (
    DetectionConsequence,
    GhostDetectorComponent,
    RadioDetectorComponent,
    RadioSourceMarkerComponent,
    SpectralMarkerComponent,
    spawn_ghost_detector,
    spawn_radio,
)

EPOCH = 100


def _room(world, title="Cellar"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _place(world, room, item, mode=ContainmentMode.ROOM_CONTENT):
    room.add_relationship(Contains(mode=mode), item.id)


def _enemy(world, room, *, strength=1.0):
    enemy = spawn_entity(
        world,
        [
            IdentityComponent(name="ghast", kind="character"),
            CharacterComponent(),
            SpectralMarkerComponent(strength=strength),
        ],
    )
    _place(world, room, enemy)
    return enemy


def _volume(detector, component_type=GhostDetectorComponent):
    return detector.get_component(component_type).volume


def test_loose_detector_on_floor_detects_enemy_in_room():
    actor = WorldActor()
    room = _room(actor.world)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)  # sitting on the floor
    _enemy(actor.world, room)

    DetectionConsequence().process(actor.world, EPOCH)

    assert _volume(detector) > 0.0


def test_detector_is_silent_without_markers():
    actor = WorldActor()
    room = _room(actor.world)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)

    DetectionConsequence().process(actor.world, EPOCH)

    assert _volume(detector) == 0.0


def test_detector_falls_silent_when_enemy_leaves():
    actor = WorldActor()
    room = _room(actor.world)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    enemy = _enemy(actor.world, room)
    consequence = DetectionConsequence()

    consequence.process(actor.world, EPOCH)
    assert _volume(detector) > 0.0

    actor.world.remove(enemy.id)
    consequence.process(actor.world, EPOCH + 1)
    assert _volume(detector) == 0.0


def test_powered_off_detector_stays_silent():
    actor = WorldActor()
    room = _room(actor.world)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    _enemy(actor.world, room)
    replace_component(
        detector, replace(detector.get_component(GhostDetectorComponent), powered=False)
    )

    DetectionConsequence().process(actor.world, EPOCH)

    assert _volume(detector) == 0.0


def test_zero_gain_detector_stays_silent():
    actor = WorldActor()
    room = _room(actor.world)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    _enemy(actor.world, room)
    replace_component(detector, replace(detector.get_component(GhostDetectorComponent), gain=0.0))

    DetectionConsequence().process(actor.world, EPOCH)

    assert _volume(detector) == 0.0


def test_gain_scales_output_volume():
    actor = WorldActor()
    room = _room(actor.world)
    full = spawn_ghost_detector(actor.world, room_id=room.id)
    half = spawn_ghost_detector(actor.world, room_id=room.id)
    replace_component(half, replace(half.get_component(GhostDetectorComponent), gain=0.5))
    _enemy(actor.world, room, strength=5.0)  # shriek-level signal

    DetectionConsequence().process(actor.world, EPOCH)

    assert _volume(half) == _volume(full) * 0.5


def test_held_detector_detects_through_its_holder():
    actor = WorldActor()
    room = _room(actor.world)
    holder = spawn_entity(
        actor.world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    _place(actor.world, room, holder)
    detector = spawn_ghost_detector(actor.world)  # uncontained, then handed to the holder
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), detector.id)
    _enemy(actor.world, room)

    DetectionConsequence().process(actor.world, EPOCH)

    assert _volume(detector) > 0.0


def test_radio_detects_radio_source():
    actor = WorldActor()
    room = _room(actor.world)
    radio = spawn_radio(actor.world, room_id=room.id)
    source = spawn_entity(
        actor.world, [IdentityComponent(name="beacon", kind="item"), RadioSourceMarkerComponent()]
    )
    _place(actor.world, room, source)

    DetectionConsequence().process(actor.world, EPOCH)

    assert radio.get_component(RadioDetectorComponent).volume > 0.0


def test_detection_pulses_a_noise_entity_in_the_room():
    actor = WorldActor()
    room = _room(actor.world)
    detector = spawn_ghost_detector(actor.world, room_id=room.id)
    _enemy(actor.world, room)

    DetectionConsequence().process(actor.world, EPOCH)

    noises = list(actor.world.query().with_all([NoiseComponent]).execute_entities())
    assert len(noises) == 1
    noise = noises[0].get_component(NoiseComponent)
    assert noise.room_id == str(room.id)
    assert noise.loudness == _volume(detector)
    assert noise.text == "wail"
    assert noise.source_entity_id == str(detector.id)


def test_stable_band_does_not_pulse_every_tick():
    actor = WorldActor()
    room = _room(actor.world)
    spawn_ghost_detector(actor.world, room_id=room.id)
    _enemy(actor.world, room)
    consequence = DetectionConsequence()

    consequence.process(actor.world, EPOCH)  # rising edge -> one pulse
    consequence.process(actor.world, EPOCH + 1)  # same band, within re-pulse window

    noises = list(actor.world.query().with_all([NoiseComponent]).execute_entities())
    assert len(noises) == 1


def test_pulsed_noise_is_audible_through_core_hearing():
    actor = WorldActor()
    room = _room(actor.world)
    listener = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Kell", kind="character"),
            CharacterComponent(),
            PerceptionComponent(active=True),
        ],
    )
    _place(actor.world, room, listener)
    spawn_ghost_detector(actor.world, room_id=room.id)
    _enemy(actor.world, room)

    DetectionConsequence().process(actor.world, EPOCH)
    events = HearingConsequence().process(actor.world, EPOCH)

    assert any(getattr(event, "text", "") == "wail" for event in events)
    assert listener.get_component(PerceptionComponent).audible_entities
