"""Out-of-tree Bunnyland plugin: monster-detecting devices (ghost detector + radio)."""

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
from .install import install_spectersim
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_ghost_detector, spawn_radio
from .spatial import holder_of, room_of

__all__ = [
    "DETECTOR_MARKER_PAIRS",
    "DETECTOR_TYPES",
    "PLUGIN_ID",
    "DetectionConsequence",
    "DetectorPoweredEvent",
    "DetectorVolumeSetEvent",
    "GhostDetectorComponent",
    "PowerDetectorHandler",
    "RadioDetectorComponent",
    "RadioSourceMarkerComponent",
    "SetDetectorVolumeHandler",
    "SpecterWorldgenHook",
    "SpectralMarkerComponent",
    "bunnyland_plugins",
    "detector_component_of",
    "holder_of",
    "install_spectersim",
    "plugin",
    "room_of",
    "spawn_ghost_detector",
    "spawn_radio",
    "spectersim_fragments",
]
