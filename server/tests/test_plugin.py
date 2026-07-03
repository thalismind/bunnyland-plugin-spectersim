from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_spectersim import (
    GhostDetectorComponent,
    RadioDetectorComponent,
    RadioSourceMarkerComponent,
    RitualKitComponent,
    SanityComponent,
    SpecterWorldgenHook,
    SpectralMarkerComponent,
    WardComponent,
    ritual_fragments,
    sanity_fragments,
    spectersim_fragments,
)
from bunnyland_spectersim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_spectersim"])
    assert [p.id for p in plugins] == [f"bunnyland_spectersim.{PLUGIN_ID}"]


def test_plugin_declares_its_contributions():
    plugin = load_modules(["bunnyland_spectersim"])[0]
    for component in (
        SpectralMarkerComponent,
        RadioSourceMarkerComponent,
        GhostDetectorComponent,
        RadioDetectorComponent,
    ):
        assert component in plugin.ecs.components
    assert SpecterWorldgenHook in plugin.content.worldgen_hooks
    assert spectersim_fragments in plugin.content.prompt_fragments


def test_plugin_is_v2():
    plugin = load_modules(["bunnyland_spectersim"])[0]
    assert plugin.version == "0.2.0"


def test_plugin_declares_v2_contributions():
    plugin = load_modules(["bunnyland_spectersim"])[0]
    for component in (SanityComponent, WardComponent, RitualKitComponent):
        assert component in plugin.ecs.components
    assert sanity_fragments in plugin.content.prompt_fragments
    assert ritual_fragments in plugin.content.prompt_fragments


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_spectersim"]), actor)
    assert applied[0].id == f"bunnyland_spectersim.{PLUGIN_ID}"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {
        "power-detector",
        "set-detector-volume",
        "draw-ward",
        "perform-ritual",
    } <= command_types
