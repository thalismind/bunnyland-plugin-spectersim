"""Marker and detector components.

Each variant uses a **separate** marker component and a **separate** detector component, so
every detector's per-tick scan is a guaranteed component-index iteration
(``world.query().with_all([MarkerType])``) rather than a filtered room walk.

Components are immutable; detection and the command handlers swap whole values with
``replace_component(entity, replace(component, ...))``.
"""

from __future__ import annotations

from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component

from .bands import FAINT, LOUD, NEAR, SILENT, volume_band

# --------------------------------------------------------------------------------------
# Markers — "this entity registers on a detector"
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SpectralMarkerComponent(Component):
    """Registers on ghost-hunting gear (monsters, spirits, the undead)."""

    strength: float = 1.0


@dataclass(frozen=True)
class RadioSourceMarkerComponent(Component):
    """Emits a broadcast a radio can pick up (transmitters, beacons, some enemies)."""

    strength: float = 1.0
    band: str = "am"


# --------------------------------------------------------------------------------------
# Detectors — devices that make noise scaled to same-room markers
# --------------------------------------------------------------------------------------


def _detector_lines(
    noun: str, sound: str, *, powered: bool, volume: float, ctx: ComponentPromptContext
) -> tuple[str, ...]:
    """Render one detector's current state as prompt text.

    First person (the holder, or the viewer standing over a loose device) reads its own
    line even when quiet; bystanders only read it once it is audibly reacting.
    """
    first = ctx.is_first_person
    subject = f"Your {noun}" if first else f"A {noun} here"
    if not powered:
        return (f"{subject} is switched off.",) if first else ()
    band = volume_band(volume)
    if band == SILENT:
        return (f"{subject} sits silent.",) if first else ()
    if band == FAINT:
        return (f"{subject} gives a faint {sound}.",)
    if band == NEAR:
        return (f"{subject} gives a steady {sound} — something marked is close.",)
    if band == LOUD:
        return (f"{subject} gives a loud {sound} — something marked is close.",)
    # SHRIEK
    return (f"{subject} gives a piercing {sound} — something marked is right here.",)


@dataclass(frozen=True)
class GhostDetectorComponent(Component):
    """A handheld ghost detector. Reacts to :class:`SpectralMarkerComponent`."""

    sound: str = "wail"
    powered: bool = True
    gain: float = 1.0
    volume: float = 0.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return _detector_lines(
            "ghost detector", self.sound, powered=self.powered, volume=self.volume, ctx=ctx
        )


@dataclass(frozen=True)
class RadioDetectorComponent(Component):
    """A handheld radio. Reacts to :class:`RadioSourceMarkerComponent`."""

    sound: str = "hiss"
    powered: bool = True
    gain: float = 1.0
    volume: float = 0.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return _detector_lines(
            "radio", self.sound, powered=self.powered, volume=self.volume, ctx=ctx
        )


#: (detector component type, marker component type) pairs driving detection generically.
DETECTOR_MARKER_PAIRS: tuple[tuple[type, type], ...] = (
    (GhostDetectorComponent, SpectralMarkerComponent),
    (RadioDetectorComponent, RadioSourceMarkerComponent),
)

#: All detector component types, for "which detector does this item carry?" lookups.
DETECTOR_TYPES: tuple[type, ...] = tuple(detector for detector, _marker in DETECTOR_MARKER_PAIRS)


def detector_component_of(entity):
    """Return the detector component present on ``entity``, or ``None``."""
    for detector_type in DETECTOR_TYPES:
        if entity.has_component(detector_type):
            return entity.get_component(detector_type)
    return None


__all__ = [
    "DETECTOR_MARKER_PAIRS",
    "DETECTOR_TYPES",
    "GhostDetectorComponent",
    "RadioDetectorComponent",
    "RadioSourceMarkerComponent",
    "SpectralMarkerComponent",
    "detector_component_of",
]
