from bunnyland.core.generation import GenerationRequest

from bunnyland_spectersim import RadioSourceMarkerComponent, SpectralMarkerComponent
from bunnyland_spectersim.enrichment import SpecterGenerationEnricher


def _components(kind, *, tags=(), description=""):
    request = GenerationRequest(
        entity_kind=kind,
        tags=tuple(tags),
        description=description,
    )
    return SpecterGenerationEnricher().enrich(request).components


def test_hostile_character_gets_spectral_marker():
    assert any(
        isinstance(component, SpectralMarkerComponent)
        for component in _components("character", tags=("monster", "hostile"))
    )


def test_hostile_detected_from_description_text():
    assert any(
        isinstance(component, SpectralMarkerComponent)
        for component in _components("character", description="a shambling undead horror")
    )


def test_benign_character_is_not_marked():
    assert not _components("character", tags=("farmer", "friendly"), description="a cheerful baker")


def test_broadcast_object_gets_radio_marker():
    assert any(
        isinstance(component, RadioSourceMarkerComponent)
        for component in _components("object", tags=("radio", "transmitter"))
    )


def test_plain_object_is_not_marked():
    assert not _components("object", tags=("wooden", "storage"))
