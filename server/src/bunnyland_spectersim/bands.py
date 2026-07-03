"""Volume banding for detector output.

Detection maps a room's total marker strength to a *loudness* (band edges below), and the
device's current ``volume`` maps to a semantic *band* label. Banding keeps text and audio
stable under tiny numeric changes and, deliberately, keeps loudness values above the
default :class:`HearingComponent` sensitivity of ``1.0`` so the device is actually heard.
"""

from __future__ import annotations

SILENT = "silent"
FAINT = "faint"
NEAR = "near"
LOUD = "loud"
SHRIEK = "shriek"

#: Bands in ascending intensity; the index is used to detect a rising edge.
BAND_ORDER = (SILENT, FAINT, NEAR, LOUD, SHRIEK)


def detected_loudness(strength_sum: float) -> float:
    """Map total same-room marker strength to a raw device loudness."""
    if strength_sum <= 0.0:
        return 0.0
    if strength_sum < 1.0:
        return 1.5
    if strength_sum < 2.0:
        return 2.5
    if strength_sum < 4.0:
        return 3.5
    return 5.0


def volume_band(volume: float) -> str:
    """Map a detector's current output volume to a semantic band."""
    if volume <= 0.0:
        return SILENT
    if volume < 2.0:
        return FAINT
    if volume < 3.0:
        return NEAR
    if volume < 4.5:
        return LOUD
    return SHRIEK


def band_rank(band: str) -> int:
    """Ascending rank of a band (``SILENT`` is ``0``)."""
    return BAND_ORDER.index(band)


__all__ = [
    "BAND_ORDER",
    "FAINT",
    "LOUD",
    "NEAR",
    "SHRIEK",
    "SILENT",
    "band_rank",
    "detected_loudness",
    "volume_band",
]
