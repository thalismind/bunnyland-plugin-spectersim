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
from .install import install_spectersim, install_spectersim_v2
from .rituals import (
    RITUAL_ACTION_DEFINITIONS,
    RITUAL_ACTION_HANDLERS,
    PresenceBanishedEvent,
    PresenceWeakenedEvent,
    RitualKitComponent,
    WardComponent,
    WardDrawnEvent,
    ritual_fragments,
)
from .sanity import SanityChangedEvent, SanityComponent, sanity_fragments

PLUGIN_ID = "bunnyland_spectersim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Spectersim",
        version="0.2.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                SpectralMarkerComponent,
                RadioSourceMarkerComponent,
                GhostDetectorComponent,
                RadioDetectorComponent,
                SanityComponent,
                WardComponent,
                RitualKitComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=DETECTOR_ACTION_HANDLERS + RITUAL_ACTION_HANDLERS,
            action_definitions=DETECTOR_ACTION_DEFINITIONS + RITUAL_ACTION_DEFINITIONS,
            typed_events=(
                DetectorPoweredEvent,
                DetectorVolumeSetEvent,
                SanityChangedEvent,
                WardDrawnEvent,
                PresenceWeakenedEvent,
                PresenceBanishedEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_spectersim, install_spectersim_v2),
        ),
        content=ContentContribution(
            prompt_fragments=(spectersim_fragments, sanity_fragments, ritual_fragments),
            worldgen_hooks=(SpecterWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
