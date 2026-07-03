"""Runtime wiring: register the detection consequence on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .detection import DetectionConsequence


def install_spectersim(actor: WorldActor) -> None:
    """Register the per-tick detection consequence (a ``service_factories`` entry)."""
    actor.register_consequence(DetectionConsequence())


__all__ = ["install_spectersim"]
