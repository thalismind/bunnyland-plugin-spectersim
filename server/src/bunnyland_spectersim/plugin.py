"""Bunnyland plugin entrypoint for the out-of-tree spectersim detector extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .commands import DETECTOR_ACTION_DEFINITIONS, DETECTOR_ACTION_HANDLERS
from .components import (
    GhostDetectorComponent,
    RadioDetectorComponent,
    RadioSourceMarkerComponent,
    SpectralMarkerComponent,
)
from .enrichment import SpecterWorldgenHook
from .events import DetectorPoweredEvent, DetectorVolumeSetEvent
from .fragments import spectersim_fragments
from .install import install_spectersim

PLUGIN_ID = "bunnyland_spectersim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Spectersim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                SpectralMarkerComponent,
                RadioSourceMarkerComponent,
                GhostDetectorComponent,
                RadioDetectorComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=DETECTOR_ACTION_HANDLERS,
            action_definitions=DETECTOR_ACTION_DEFINITIONS,
            typed_events=(DetectorPoweredEvent, DetectorVolumeSetEvent),
        ),
        runtime=RuntimeContribution(service_factories=(install_spectersim,)),
        content=ContentContribution(
            prompt_fragments=(spectersim_fragments,),
            worldgen_hooks=(SpecterWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
