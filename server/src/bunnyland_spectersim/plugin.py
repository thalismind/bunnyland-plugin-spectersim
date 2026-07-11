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
from .enrichment import SpecterGenerationEnricher
from .events import DetectorPoweredEvent, DetectorVolumeSetEvent
from .evidence import (
    EVIDENCE_ACTION_DEFINITIONS,
    EVIDENCE_ACTION_HANDLERS,
    EvidenceComponent,
    EvidenceLogComponent,
    EvidenceRecordedEvent,
    evidence_fragments,
)
from .fog import FogChangedEvent, FogComponent, fog_fragments
from .fragments import spectersim_fragments
from .install import (
    install_spectersim,
    install_spectersim_v2,
    install_spectersim_v3,
)
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

PLUGIN_ID = "bunnyland.spectersim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Spectersim",
        version="0.3.0",
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
                EvidenceComponent,
                EvidenceLogComponent,
                FogComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=(
                DETECTOR_ACTION_HANDLERS + RITUAL_ACTION_HANDLERS + EVIDENCE_ACTION_HANDLERS
            ),
            action_definitions=(
                DETECTOR_ACTION_DEFINITIONS
                + RITUAL_ACTION_DEFINITIONS
                + EVIDENCE_ACTION_DEFINITIONS
            ),
            typed_events=(
                DetectorPoweredEvent,
                DetectorVolumeSetEvent,
                SanityChangedEvent,
                WardDrawnEvent,
                PresenceWeakenedEvent,
                PresenceBanishedEvent,
                EvidenceRecordedEvent,
                FogChangedEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(
                install_spectersim,
                install_spectersim_v2,
                install_spectersim_v3,
            ),
        ),
        content=ContentContribution(
            prompt_fragments=(
                spectersim_fragments,
                sanity_fragments,
                ritual_fragments,
                evidence_fragments,
                fog_fragments,
            ),
            generation_enrichers=(SpecterGenerationEnricher(),),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
