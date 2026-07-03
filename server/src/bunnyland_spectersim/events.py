"""Domain events emitted by the detector verbs."""

from __future__ import annotations

from bunnyland.core.events import DomainEvent


class DetectorPoweredEvent(DomainEvent):
    """A character switched a detector on or off."""

    item_id: str
    powered: bool
    sound: str = ""


class DetectorVolumeSetEvent(DomainEvent):
    """A character adjusted a detector's volume knob."""

    item_id: str
    gain: float


__all__ = ["DetectorPoweredEvent", "DetectorVolumeSetEvent"]
