"""Out-of-tree Bunnyland plugin: monster-detecting devices (ghost detector + radio).

v2 adds two bundled mechanics: a **sanity** dread meter and **rituals/wards** for banishing
spectral presences.
"""

from .commands import PowerDetectorHandler, SetDetectorVolumeHandler
from .components import (
    DETECTOR_MARKER_PAIRS,
    DETECTOR_TYPES,
    GhostDetectorComponent,
    RadioDetectorComponent,
    RadioSourceMarkerComponent,
    SpectralMarkerComponent,
    detector_component_of,
)
from .detection import DetectionConsequence
from .enrichment import SpecterWorldgenHook
from .events import DetectorPoweredEvent, DetectorVolumeSetEvent
from .fragments import spectersim_fragments
from .install import install_spectersim, install_spectersim_v2
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_ghost_detector, spawn_radio, spawn_ritual_kit, spawn_ward
from .rituals import (
    DrawWardHandler,
    PerformRitualHandler,
    PresenceBanishedEvent,
    PresenceWeakenedEvent,
    RitualKitComponent,
    WardComponent,
    WardConsequence,
    WardDrawnEvent,
    ritual_fragments,
)
from .sanity import (
    SanityChangedEvent,
    SanityComponent,
    SanityConsequence,
    sanity_band,
    sanity_fragments,
)
from .spatial import holder_of, room_of

__all__ = [
    "DETECTOR_MARKER_PAIRS",
    "DETECTOR_TYPES",
    "PLUGIN_ID",
    "DetectionConsequence",
    "DetectorPoweredEvent",
    "DetectorVolumeSetEvent",
    "DrawWardHandler",
    "GhostDetectorComponent",
    "PerformRitualHandler",
    "PowerDetectorHandler",
    "PresenceBanishedEvent",
    "PresenceWeakenedEvent",
    "RadioDetectorComponent",
    "RadioSourceMarkerComponent",
    "RitualKitComponent",
    "SanityChangedEvent",
    "SanityComponent",
    "SanityConsequence",
    "SetDetectorVolumeHandler",
    "SpecterWorldgenHook",
    "SpectralMarkerComponent",
    "WardComponent",
    "WardConsequence",
    "WardDrawnEvent",
    "bunnyland_plugins",
    "detector_component_of",
    "holder_of",
    "install_spectersim",
    "install_spectersim_v2",
    "plugin",
    "ritual_fragments",
    "room_of",
    "sanity_band",
    "sanity_fragments",
    "spawn_ghost_detector",
    "spawn_radio",
    "spawn_ritual_kit",
    "spawn_ward",
    "spectersim_fragments",
]
