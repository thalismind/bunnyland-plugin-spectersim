"""Rituals and wards: place protection, then banish the marked presence.

Two cooperating pieces of state:

- :class:`WardComponent` marks a *room* as protected (drawn straight onto the room) or sits
  on a placed ward *entity* resting in a room. Either way the room counts as warded.
- :class:`RitualKitComponent` is a held item a character channels to actively banish a
  spectral presence in the room they stand in.

A per-tick :class:`WardConsequence` passively weakens and finally banishes any
:class:`~bunnyland_spectersim.components.SpectralMarkerComponent` caught in a warded room;
the ``perform-ritual`` verb does the same thing faster and on demand. "Banishing" simply
strips the ``SpectralMarkerComponent`` — the entity survives, it just stops registering as a
spectral presence — which is the cleanest reversible outcome.

Verb validation follows the project order: invalid id -> missing entity -> not held ->
wrong kind -> invalid state -> apply.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import RoomComponent
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import contents, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_entity,
)
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import SpectralMarkerComponent
from .spatial import holder_of, room_of

#: A presence at or below this marker strength is banished outright.
BANISH_THRESHOLD = 0.05
#: Sanity-free passive erosion a ward applies to a trapped presence each tick.
WARD_WEAKEN_PER_TICK = 0.25


# --------------------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class WardComponent(Component):
    """Protects a room (drawn on the room, or on a ward entity resting in the room)."""

    strength: float = 1.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return ("A ward here holds the space against spectral presences.",)


@dataclass(frozen=True)
class RitualKitComponent(Component):
    """A held kit that channels a banishing ritual. ``potency`` is banished per attempt."""

    potency: float = 0.5

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        return ("You carry a ritual kit ready to banish a presence.",)


# --------------------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------------------


class WardDrawnEvent(DomainEvent):
    """A character drew a protective ward in a room."""

    room_id_warded: str


class PresenceWeakenedEvent(DomainEvent):
    """A warded room or ritual weakened a spectral presence."""

    target_id: str
    strength: float


class PresenceBanishedEvent(DomainEvent):
    """A spectral presence lost its marker and was banished."""

    target_id: str


# --------------------------------------------------------------------------------------
# Ward helpers
# --------------------------------------------------------------------------------------


def _warded_room_ids(world: World) -> set[str]:
    """Room ids that are warded, whether the ward sits on the room or on a placed entity."""
    warded: set[str] = set()
    for entity in world.query().with_all([WardComponent]).execute_entities():
        if entity.has_component(RoomComponent):
            warded.add(str(entity.id))
            continue
        room = room_of(world, entity.id)
        if room is not None:
            warded.add(str(room.id))
    return warded


def _ward_strength_for_room(world: World, room: Entity) -> float:
    """Strongest ward protecting ``room`` (on the room itself or a ward entity within)."""
    best = 0.0
    if room.has_component(WardComponent):
        best = room.get_component(WardComponent).strength
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if entity.has_component(WardComponent):
            best = max(best, entity.get_component(WardComponent).strength)
    return best


def _weaken_presence(
    entity: Entity, amount: float, epoch: int, *, room_id: str | None
) -> DomainEvent:
    """Reduce a presence's marker strength, banishing it when it is spent."""
    marker = entity.get_component(SpectralMarkerComponent)
    new_strength = marker.strength - amount
    if new_strength <= BANISH_THRESHOLD:
        entity.remove_component(SpectralMarkerComponent)
        return PresenceBanishedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.ROOM,
                room_id=room_id,
                target_ids=(str(entity.id),),
                target_id=str(entity.id),
            )
        )
    replace_component(entity, replace(marker, strength=new_strength))
    return PresenceWeakenedEvent(
        **event_base(
            epoch,
            default_visibility=EventVisibility.ROOM,
            room_id=room_id,
            target_ids=(str(entity.id),),
            target_id=str(entity.id),
            strength=new_strength,
        )
    )


class WardConsequence:
    """Passively weaken and banish spectral presences standing in warded rooms."""

    def __init__(self, *, weaken_per_tick: float = WARD_WEAKEN_PER_TICK):
        self.weaken_per_tick = weaken_per_tick

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        warded = _warded_room_ids(world)
        if not warded:
            return []
        events: list[DomainEvent] = []
        for presence in list(world.query().with_all([SpectralMarkerComponent]).execute_entities()):
            room = room_of(world, presence.id)
            if room is None or str(room.id) not in warded:
                continue
            amount = self.weaken_per_tick * _ward_strength_for_room(world, room)
            events.append(_weaken_presence(presence, amount, epoch, room_id=str(room.id)))
        return events


# --------------------------------------------------------------------------------------
# Verbs
# --------------------------------------------------------------------------------------


class DrawWardHandler:
    """Draw a protective ward in the room you stand in, optionally consuming a reagent."""

    command_type = "draw-ward"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")
        if room.has_component(WardComponent):
            return rejected("this room is already warded")

        reagent = None
        raw_reagent = command.payload.get("reagent_id")
        if raw_reagent is not None:
            reagent_id, reagent, rejection = require_entity(
                ctx,
                raw_reagent,
                invalid_reason="invalid reagent id",
                missing_reason="reagent does not exist",
            )
            if rejection is not None:
                return rejection
            holder = holder_of(ctx.world, reagent_id)
            if holder is None or holder.id != character_id:
                return rejected("you are not holding that reagent")

        strength = float(command.payload.get("strength", 1.0))
        replace_component(room, WardComponent(strength=strength))
        if reagent is not None:
            ctx.world.remove(reagent.id)
        return ok(
            WardDrawnEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(room.id),),
                    room_id_warded=str(room.id),
                )
            )
        )


class PerformRitualHandler:
    """Channel a held ritual kit to weaken (and eventually banish) a spectral presence."""

    command_type = "perform-ritual"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        kit_id, kit, rejection = require_entity(
            ctx,
            command.payload.get("kit_id"),
            invalid_reason="invalid kit id",
            missing_reason="ritual kit does not exist",
        )
        if rejection is not None:
            return rejection
        holder = holder_of(ctx.world, kit_id)
        if holder is None or holder.id != character_id:
            return rejected("you are not holding that ritual kit")
        if not kit.has_component(RitualKitComponent):
            return rejected("that is not a ritual kit")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")

        presence, rejection = self._resolve_target(ctx, room, command)
        if rejection is not None:
            return rejection

        potency = kit.get_component(RitualKitComponent).potency
        event = _weaken_presence(presence, potency, ctx.epoch, room_id=str(room.id))
        return ok(event)

    def _resolve_target(self, ctx: HandlerContext, room, command: SubmittedCommand):
        raw_target = command.payload.get("target_id")
        if raw_target is not None:
            target_id, target, rejection = require_entity(
                ctx,
                raw_target,
                invalid_reason="invalid target id",
                missing_reason="target does not exist",
            )
            if rejection is not None:
                return None, rejection
            presence_room = room_of(ctx.world, target_id)
            if presence_room is None or presence_room.id != room.id:
                return None, rejected("target is not here")
            if not target.has_component(SpectralMarkerComponent):
                return None, rejected("target is not a spectral presence")
            return target, None
        presence = _first_presence_in_room(ctx.world, room)
        if presence is None:
            return None, rejected("there is nothing to banish here")
        return presence, None


def _first_presence_in_room(world: World, room) -> Entity | None:
    presences: list[Entity] = []
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if entity.has_component(SpectralMarkerComponent):
            presences.append(entity)
    presences.sort(key=lambda entity: str(entity.id))
    return presences[0] if presences else None


# --------------------------------------------------------------------------------------
# Action definitions
# --------------------------------------------------------------------------------------


DRAW_WARD_DEF = ActionDefinition(
    command_type="draw-ward",
    title="Draw ward",
    description="Draw a protective ward in the room you are in.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.EXTENDED),
    arguments={
        "reagent_id": ActionArgument(
            title="Reagent",
            description="Optional held item consumed to draw the ward.",
            kind="entity",
        ),
        "strength": ActionArgument(
            title="Strength",
            description="How strong the ward is (default 1.0).",
            kind="number",
        ),
    },
)

PERFORM_RITUAL_DEF = ActionDefinition(
    command_type="perform-ritual",
    title="Perform ritual",
    description="Channel a held ritual kit to banish a spectral presence in the room.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.MAJOR),
    arguments={
        "kit_id": ActionArgument(
            title="Ritual kit",
            description="The ritual kit you are holding.",
            kind="entity",
            required=True,
        ),
        "target_id": ActionArgument(
            title="Presence",
            description="The presence to banish; omit to target the first one here.",
            kind="entity",
        ),
    },
)

RITUAL_ACTION_DEFINITIONS = (DRAW_WARD_DEF, PERFORM_RITUAL_DEF)
RITUAL_ACTION_HANDLERS = (DrawWardHandler, PerformRitualHandler)


# --------------------------------------------------------------------------------------
# Prompt fragments
# --------------------------------------------------------------------------------------


def _ward_entity_for_room(world: World, room: Entity) -> Entity | None:
    if room.has_component(WardComponent):
        return room
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if entity.has_component(WardComponent):
            return entity
    return None


def ritual_fragments(world: World, character: Entity) -> list[str]:
    """Ward protection on the room, plus the first-person ritual-kit line if carried."""
    lines: list[str] = []
    if character is None:
        return lines
    room = room_of(world, character.id)
    if room is not None:
        ward = _ward_entity_for_room(world, room)
        if ward is not None:
            ctx = ComponentPromptContext.for_entity(world, ward, room=room)
            lines.extend(ward.get_component(WardComponent).prompt_fragments(ctx))
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(RitualKitComponent):
            ctx = ComponentPromptContext.for_entity(
                world, item, perspective=PromptPerspective(viewer=item)
            )
            lines.extend(item.get_component(RitualKitComponent).prompt_fragments(ctx))
    return sorted(dict.fromkeys(lines))


__all__ = [
    "BANISH_THRESHOLD",
    "DRAW_WARD_DEF",
    "PERFORM_RITUAL_DEF",
    "RITUAL_ACTION_DEFINITIONS",
    "RITUAL_ACTION_HANDLERS",
    "WARD_WEAKEN_PER_TICK",
    "DrawWardHandler",
    "PerformRitualHandler",
    "PresenceBanishedEvent",
    "PresenceWeakenedEvent",
    "RitualKitComponent",
    "WardComponent",
    "WardConsequence",
    "WardDrawnEvent",
    "ritual_fragments",
]
