"""Runtime wiring: register the per-tick consequences on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .detection import DetectionConsequence
from .rituals import WardConsequence
from .sanity import SanityConsequence


def install_spectersim(actor: WorldActor) -> None:
    """Register the v1 detection consequence (a ``service_factories`` entry)."""
    actor.register_consequence(DetectionConsequence())


def install_spectersim_v2(actor: WorldActor) -> None:
    """Register the v2 sanity and ward consequences (a ``service_factories`` entry)."""
    actor.register_consequence(SanityConsequence())
    actor.register_consequence(WardConsequence())


__all__ = ["install_spectersim", "install_spectersim_v2"]
