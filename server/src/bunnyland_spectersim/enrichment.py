"""World-generation enrichment: tag generated enemies and broadcasters with markers.

Generated entities expose semantic ``tags``/``wants``/``needs`` and an intent
``description``. This hook scans that text and attaches the detectable marker so detectors
have something to react to in generated worlds — without the core generator knowing this
plugin exists.
"""

from __future__ import annotations

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .components import RadioSourceMarkerComponent, SpectralMarkerComponent

#: Words that mark a generated character as something ghost gear should register.
HOSTILE_TERMS = (
    "hostile",
    "enemy",
    "monster",
    "monstrous",
    "ghost",
    "ghostly",
    "spirit",
    "specter",
    "spectre",
    "spectral",
    "wraith",
    "phantom",
    "haunt",
    "undead",
    "zombie",
    "demon",
    "predator",
    "threat",
    "aggressive",
    "kaiju",
)

#: Words that mark a generated object as a radio source.
BROADCAST_TERMS = (
    "radio",
    "transmitter",
    "transmit",
    "beacon",
    "broadcast",
    "antenna",
    "signal",
    "receiver",
    "transceiver",
)


def _text(request: GenerationRequest) -> str:
    return " ".join(
        (
            request.entity_kind,
            request.description,
            *request.tags,
            *request.capabilities,
        )
    ).casefold()


def _mentions(request: GenerationRequest, terms: tuple[str, ...]) -> bool:
    text = _text(request)
    return any(term in text for term in terms)


class SpecterGenerationEnricher:
    """Plan detectable markers before a generated entity is instantiated."""

    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        components = []
        if request.entity_kind == "character" and _mentions(request, HOSTILE_TERMS):
            components.append(SpectralMarkerComponent())
        if request.entity_kind in {"object", "item"} and _mentions(request, BROADCAST_TERMS):
            components.append(RadioSourceMarkerComponent())
        return GenerationDelta(components=tuple(components))


__all__ = ["BROADCAST_TERMS", "HOSTILE_TERMS", "SpecterGenerationEnricher"]
