"""Prompt fragment provider.

A single ``(world, character) -> list[str]`` provider feeds both the LLM actor context and
the human character-chat prompt. It renders any detector the character can perceive —
carried in their own inventory *or* resting in the room — so a device on the floor is still
described.

A detector component lives on the *device* entity, not the character, so the context's
``is_first_person`` (viewer == component's entity) is only true when we deliberately view
*from* the device. We do that for a device the character is holding, so the holder reads
"Your ghost detector…" while bystanders (and anyone near a floor-resting device) read
"A ghost detector here…".
"""

from __future__ import annotations

from bunnyland.core import reachable_ids
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective
from relics import Entity, World

from .components import DETECTOR_TYPES
from .spatial import holder_of


def spectersim_fragments(world: World, character: Entity) -> list[str]:
    lines: list[str] = []
    base = ComponentPromptContext.for_entity(world, character)
    # reachable_ids() returns only live ids: the character, its inventory, its room, and the
    # room's contents — i.e. both held and floor-resting detectors.
    for entity_id in reachable_ids(world, character):
        entity = world.get_entity(entity_id)
        if not any(entity.has_component(detector_type) for detector_type in DETECTOR_TYPES):
            continue
        held = holder_of(world, entity_id)
        first_person = held is not None and held.id == character.id
        # Viewing "from" the device makes ctx.is_first_person true for its holder.
        perspective = PromptPerspective(viewer=entity if first_person else character)
        ctx = ComponentPromptContext.for_entity(
            world, entity, perspective=perspective, room=base.room, target=character
        )
        for detector_type in DETECTOR_TYPES:
            if entity.has_component(detector_type):
                lines.extend(entity.get_component(detector_type).prompt_fragments(ctx))
    return sorted(dict.fromkeys(lines))


__all__ = ["spectersim_fragments"]
