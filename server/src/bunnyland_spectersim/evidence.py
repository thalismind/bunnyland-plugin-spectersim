"""EVP / evidence log: capture eerie proof of a spectral presence (v3).

An investigator builds a private **evidence log** as they sweep haunted rooms. Evidence is
recordable only when the room actually holds something to record — a
:class:`~bunnyland_spectersim.components.SpectralMarkerComponent` presence, and/or a detector
that is audibly reacting (``volume > 0``). The ``log-reading`` verb captures whatever is
present into the investigator's own :class:`EvidenceLogComponent`; the log is the character's
per-character memory of the haunting, so its summary line is first-person only.

Evidence content is fully **deterministic** — derived from stable entity ids and the world
epoch via :func:`hashlib.sha1`, never from ``random`` or wall-clock time — so a replayed world
produces an identical log.

Verb validation follows the project order: invalid id -> missing entity -> not held ->
wrong kind -> invalid state -> apply.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.ecs import contents, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
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

from .components import SpectralMarkerComponent, detector_component_of
from .spatial import holder_of, room_of

# --------------------------------------------------------------------------------------
# Evidence kinds
# --------------------------------------------------------------------------------------

#: The eerie things an investigator can capture from a spectral presence, in stable order.
EVP = "EVP capture"
COLD_SPOT = "cold spot"
ORB = "orb sighting"
APPARITION = "apparition glimpse"

#: Kinds a *presence* can yield, indexed deterministically by a stable digest.
PRESENCE_KINDS: tuple[str, ...] = (EVP, COLD_SPOT, ORB, APPARITION)

#: A reacting detector always yields this kind, regardless of any presence.
DETECTOR_SPIKE = "detector spike"


def _stable_index(*parts: object) -> int:
    """A deterministic non-negative int from stable parts (id strings, epoch).

    Uses :func:`hashlib.sha1` rather than :func:`hash` so it never depends on
    ``PYTHONHASHSEED`` and a replayed world reproduces the same evidence.
    """
    digest = hashlib.sha1("|".join(str(part) for part in parts).encode()).digest()
    return int.from_bytes(digest[:4], "big")


def _presence_kind(source_id: str, epoch: int) -> str:
    return PRESENCE_KINDS[_stable_index(source_id, epoch) % len(PRESENCE_KINDS)]


# --------------------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceEntry:
    """One captured piece of evidence. Immutable; entries are only ever appended."""

    kind: str
    text: str
    room_id: str = ""
    recorded_at_epoch: int = 0


@dataclass(frozen=True)
class EvidenceComponent(Component):
    """Marks a held item as an EVP recorder that can capture evidence."""

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        return ("You carry an EVP recorder ready to capture evidence.",)


@dataclass(frozen=True)
class EvidenceLogComponent(Component):
    """An investigator's private log of captured evidence."""

    entries: tuple[EvidenceEntry, ...] = ()

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        # The log is a private memory: only its owner reads its contents.
        if not ctx.is_first_person or not self.entries:
            return ()
        return (_log_summary(self.entries),)


def _log_summary(entries: tuple[EvidenceEntry, ...]) -> str:
    """Deterministic one-line tally of a log's evidence, grouped by kind."""
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.kind] = counts.get(entry.kind, 0) + 1
    parts = [f"{count} {kind}{'s' if count != 1 else ''}" for kind, count in sorted(counts.items())]
    return "Your evidence log holds " + ", ".join(parts) + "."


# --------------------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------------------


class EvidenceRecordedEvent(DomainEvent):
    """An investigator recorded new evidence into their log."""

    count: int
    kinds: tuple[str, ...]


# --------------------------------------------------------------------------------------
# Room scanning
# --------------------------------------------------------------------------------------


def _presences_in_room(world: World, room: Entity) -> list[Entity]:
    presences: list[Entity] = []
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if entity.has_component(SpectralMarkerComponent):
            presences.append(entity)
    presences.sort(key=lambda entity: str(entity.id))
    return presences


def _reacting(entity: Entity) -> bool:
    component = detector_component_of(entity)
    return component is not None and component.powered and component.volume > 0.0


def _detector_is_reacting(world: World, room: Entity) -> bool:
    """True when any powered detector in the room (held or loose) is audibly reacting."""
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        # A loose detector on the floor, or one carried by someone standing here.
        if _reacting(entity):
            return True
        for held_id in contents(entity):
            if world.has_entity(held_id) and _reacting(world.get_entity(held_id)):
                return True
    return False


def _collect_evidence(world: World, room: Entity, epoch: int) -> tuple[EvidenceEntry, ...]:
    """Deterministically capture the room's current spectral evidence."""
    room_id = str(room.id)
    entries: list[EvidenceEntry] = []
    for presence in _presences_in_room(world, room):
        kind = _presence_kind(str(presence.id), epoch)
        entries.append(
            EvidenceEntry(
                kind=kind,
                text=f"{kind} logged near {presence.id} in {room_id}",
                room_id=room_id,
                recorded_at_epoch=epoch,
            )
        )
    if _detector_is_reacting(world, room):
        entries.append(
            EvidenceEntry(
                kind=DETECTOR_SPIKE,
                text=f"{DETECTOR_SPIKE} logged in {room_id}",
                room_id=room_id,
                recorded_at_epoch=epoch,
            )
        )
    return tuple(entries)


# --------------------------------------------------------------------------------------
# Verb
# --------------------------------------------------------------------------------------


class LogReadingHandler:
    """Capture the room's spectral evidence into the investigator's log.

    With ``recorder_id`` the investigator must be holding that EVP recorder; without it a
    bare-handed investigator can still note evidence in a haunted room.
    """

    command_type = "log-reading"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection

        raw_recorder = command.payload.get("recorder_id")
        if raw_recorder is not None:
            recorder_id, recorder, rejection = require_entity(
                ctx,
                raw_recorder,
                invalid_reason="invalid recorder id",
                missing_reason="recorder does not exist",
            )
            if rejection is not None:
                return rejection
            holder = holder_of(ctx.world, recorder_id)
            if holder is None or holder.id != character_id:
                return rejected("you are not holding that recorder")
            if not recorder.has_component(EvidenceComponent):
                return rejected("that is not a recorder")

        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")

        evidence = _collect_evidence(ctx.world, room, ctx.epoch)
        if not evidence:
            return rejected("there is nothing to record here")

        log = (
            character.get_component(EvidenceLogComponent)
            if character.has_component(EvidenceLogComponent)
            else EvidenceLogComponent()
        )
        updated = replace(log, entries=log.entries + evidence)
        replace_component(character, updated)
        return ok(
            EvidenceRecordedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    count=len(evidence),
                    kinds=tuple(entry.kind for entry in evidence),
                )
            )
        )


# --------------------------------------------------------------------------------------
# Action definition
# --------------------------------------------------------------------------------------


LOG_READING_DEF = ActionDefinition(
    command_type="log-reading",
    title="Log reading",
    description="Record and review spectral evidence from the room into your log.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "recorder_id": ActionArgument(
            title="Recorder",
            description="Optional EVP recorder you are holding.",
            kind="entity",
        ),
    },
)

EVIDENCE_ACTION_DEFINITIONS = (LOG_READING_DEF,)
EVIDENCE_ACTION_HANDLERS = (LogReadingHandler,)


# --------------------------------------------------------------------------------------
# Prompt fragments
# --------------------------------------------------------------------------------------


def evidence_fragments(world: World, character: Entity) -> list[str]:
    """First-person recorder + evidence-log lines for the investigator's own prompt."""
    lines: list[str] = []
    if character is None:
        return lines
    ctx = ComponentPromptContext.for_entity(world, character)
    if character.has_component(EvidenceLogComponent):
        lines.extend(character.get_component(EvidenceLogComponent).prompt_fragments(ctx))
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(EvidenceComponent):
            item_ctx = ComponentPromptContext.for_entity(
                world, item, perspective=PromptPerspective(viewer=item)
            )
            lines.extend(item.get_component(EvidenceComponent).prompt_fragments(item_ctx))
    return sorted(dict.fromkeys(lines))


__all__ = [
    "APPARITION",
    "COLD_SPOT",
    "DETECTOR_SPIKE",
    "EVIDENCE_ACTION_DEFINITIONS",
    "EVIDENCE_ACTION_HANDLERS",
    "EVP",
    "LOG_READING_DEF",
    "ORB",
    "PRESENCE_KINDS",
    "EvidenceComponent",
    "EvidenceEntry",
    "EvidenceLogComponent",
    "EvidenceRecordedEvent",
    "LogReadingHandler",
    "evidence_fragments",
]
