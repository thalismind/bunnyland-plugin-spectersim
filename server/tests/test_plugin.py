from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins

from bunnyland_spectersim import (
    EvidenceComponent,
    EvidenceLogComponent,
    FogComponent,
    GhostDetectorComponent,
    RadioDetectorComponent,
    RadioSourceMarkerComponent,
    RitualKitComponent,
    SanityComponent,
    SpecterGenerationEnricher,
    SpectralMarkerComponent,
    WardComponent,
    evidence_fragments,
    fog_fragments,
    ritual_fragments,
    sanity_fragments,
    spectersim_fragments,
)
from bunnyland_spectersim.integration_3d import install_spectersim_3d
from bunnyland_spectersim.plugin import PLUGIN_ID
from bunnyland_spectersim.plugin import bunnyland_plugins as _plugins


def test_plugin_loads_with_module_qualified_id():
    plugins = _plugins()
    assert [p.id for p in plugins] == [PLUGIN_ID]
    assert plugins[0].dependencies.integrates_with == ("bunnyland.3d",)
    assert plugins[0].runtime.integration_factories == (install_spectersim_3d,)


def test_plugin_declares_its_contributions():
    plugin = _plugins()[0]
    for component in (
        SpectralMarkerComponent,
        RadioSourceMarkerComponent,
        GhostDetectorComponent,
        RadioDetectorComponent,
    ):
        assert component in plugin.ecs.components
    assert isinstance(plugin.content.generation_enrichers[0], SpecterGenerationEnricher)
    assert spectersim_fragments in plugin.content.prompt_fragments


def test_plugin_is_v3():
    plugin = _plugins()[0]
    assert plugin.version == "0.3.0"


def test_plugin_declares_v2_contributions():
    plugin = _plugins()[0]
    for component in (SanityComponent, WardComponent, RitualKitComponent):
        assert component in plugin.ecs.components
    assert sanity_fragments in plugin.content.prompt_fragments
    assert ritual_fragments in plugin.content.prompt_fragments


def test_plugin_declares_v3_contributions():
    plugin = _plugins()[0]
    for component in (EvidenceComponent, EvidenceLogComponent, FogComponent):
        assert component in plugin.ecs.components
    assert evidence_fragments in plugin.content.prompt_fragments
    assert fog_fragments in plugin.content.prompt_fragments


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(_plugins(), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {
        "power-detector",
        "set-detector-volume",
        "draw-ward",
        "perform-ritual",
        "log-reading",
    } <= command_types
