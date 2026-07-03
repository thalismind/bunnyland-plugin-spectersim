"""Player/AI verbs for a held detector: power on/off and adjust volume.

Both verbs act only on a detector the character is **holding**. Passive detection does not
need a holder — a powered device on the floor still works — but *changing* a device's
settings requires having it in hand. Validation order matches the project convention:
invalid id -> missing entity -> not held -> not a detector -> invalid argument -> apply.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import HandlerContext, HandlerResult, ok, rejected, require_entity

from .components import detector_component_of
from .events import DetectorPoweredEvent, DetectorVolumeSetEvent
from .spatial import holder_of, room_of


def _held_detector(ctx: HandlerContext, command: SubmittedCommand):
    """Resolve (character_id, item, detector_component) or a rejection HandlerResult."""
    character_id, _character, rejection = require_entity(
        ctx,
        command.character_id,
        invalid_reason="invalid character id",
        missing_reason="character does not exist",
    )
    if rejection is not None:
        return None, rejection
    item_id, item, rejection = require_entity(
        ctx,
        command.payload.get("item_id"),
        invalid_reason="invalid item id",
        missing_reason="item does not exist",
    )
    if rejection is not None:
        return None, rejection
    holder = holder_of(ctx.world, item_id)
    if holder is None or holder.id != character_id:
        return None, rejected("you are not holding that detector")
    component = detector_component_of(item)
    if component is None:
        return None, rejected("that is not a detector")
    return (character_id, item, component), None


def _room_id(ctx: HandlerContext, character_id) -> str | None:
    room = room_of(ctx.world, character_id)
    return str(room.id) if room is not None else None


class PowerDetectorHandler:
    """Switch a held detector on or off (toggles when ``on`` is omitted)."""

    command_type = "power-detector"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        resolved, rejection = _held_detector(ctx, command)
        if rejection is not None:
            return rejection
        character_id, item, component = resolved
        raw_on = command.payload.get("on")
        powered = (not component.powered) if raw_on is None else bool(raw_on)
        replace_component(item, replace(component, powered=powered))
        return ok(
            DetectorPoweredEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=_room_id(ctx, character_id),
                    target_ids=(str(item.id),),
                    item_id=str(item.id),
                    powered=powered,
                    sound=component.sound,
                )
            )
        )


class SetDetectorVolumeHandler:
    """Set a held detector's volume knob (``gain``), 0.0-1.0."""

    command_type = "set-detector-volume"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        resolved, rejection = _held_detector(ctx, command)
        if rejection is not None:
            return rejection
        character_id, item, component = resolved
        try:
            level = float(command.payload["level"])
        except (KeyError, TypeError, ValueError):
            return rejected("volume level must be a number")
        if not 0.0 <= level <= 1.0:
            return rejected("volume must be between 0 and 1")
        replace_component(item, replace(component, gain=level))
        return ok(
            DetectorVolumeSetEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=_room_id(ctx, character_id),
                    target_ids=(str(item.id),),
                    item_id=str(item.id),
                    gain=level,
                )
            )
        )


POWER_DEF = ActionDefinition(
    command_type="power-detector",
    title="Power detector",
    description="Switch a detector you are holding on or off.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "item_id": ActionArgument(
            title="Detector", description="The detector to toggle.", kind="entity", required=True
        ),
        "on": ActionArgument(
            title="On",
            description="True to switch on, false to switch off; omit to toggle.",
            kind="boolean",
        ),
    },
)

VOLUME_DEF = ActionDefinition(
    command_type="set-detector-volume",
    title="Set detector volume",
    description="Adjust the volume of a detector you are holding (0.0 to 1.0).",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "item_id": ActionArgument(
            title="Detector", description="The detector to adjust.", kind="entity", required=True
        ),
        "level": ActionArgument(
            title="Level",
            description="Volume from 0.0 (silent) to 1.0 (full).",
            kind="number",
            required=True,
        ),
    },
)

DETECTOR_ACTION_DEFINITIONS = (POWER_DEF, VOLUME_DEF)
DETECTOR_ACTION_HANDLERS = (PowerDetectorHandler, SetDetectorVolumeHandler)


__all__ = [
    "DETECTOR_ACTION_DEFINITIONS",
    "DETECTOR_ACTION_HANDLERS",
    "POWER_DEF",
    "VOLUME_DEF",
    "PowerDetectorHandler",
    "SetDetectorVolumeHandler",
]
