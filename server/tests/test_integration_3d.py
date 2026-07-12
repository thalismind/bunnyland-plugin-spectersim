from __future__ import annotations

import sys
from types import SimpleNamespace

from bunnyland_spectersim.integration_3d import install_spectersim_3d


class _Value:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def _fake_3d():
    calls = SimpleNamespace(
        particle_systems=[], effects=[], state_rules=[], models=[], visuals=[]
    )

    def record(name):
        def inner(_actor, owner, values):
            getattr(calls, name).append((owner, tuple(values)))

        return inner

    value_names = (
        "EntityVisualContribution",
        "EntityVisualRule",
        "ModelAsset",
        "ModelTransform",
        "ParticleSystem3D",
        "PrimitivePart3D",
        "ProceduralModelSource",
        "VisualEffectDefinition",
        "VisualEffectParticleLayer",
        "VisualEffectStateRule",
        "VisualMaterial3D",
        "VisualNodePatch",
    )
    module = SimpleNamespace(
        register_entity_visuals=record("visuals"),
        register_models=record("models"),
        register_particle_systems=record("particle_systems"),
        register_visual_effect_state_rules=record("state_rules"),
        register_visual_effects=record("effects"),
    )
    for name in value_names:
        setattr(module, name, _Value)
    return module, calls


def test_plugin_stays_independent_when_3d_is_disabled():
    sys.modules.pop("bunnyland_3d", None)
    context = SimpleNamespace(plugins=SimpleNamespace(enabled=lambda _plugin_id: False))

    install_spectersim_3d(SimpleNamespace(), context)

    assert "bunnyland_3d" not in sys.modules


def test_specter_and_ward_register_persistent_effects_and_keep_ward_model(monkeypatch):
    fake, calls = _fake_3d()
    monkeypatch.setitem(sys.modules, "bunnyland_3d", fake)
    context = SimpleNamespace(plugins=SimpleNamespace(enabled=lambda _plugin_id: True))

    install_spectersim_3d(SimpleNamespace(), context)

    assert calls.particle_systems[0][0] == "bunnyland.spectersim"
    definitions = calls.effects[0][1]
    assert [definition.args[0] for definition in definitions] == [
        "bunnyland.spectersim/ward-aura",
        "bunnyland.spectersim/specter",
    ]
    specter_colors = [
        layer.kwargs["color"]
        for layer in definitions[1].kwargs["particle_layers"]
    ]
    assert specter_colors == ["#b9f5ff", "#68d8c0"]
    assert [rule.args[0] for rule in calls.state_rules[0][1]] == [
        "bunnyland.spectersim/ward-state",
        "bunnyland.spectersim/specter-state",
    ]
    assert calls.models[0][1][0].kwargs["key"] == "bunnyland.spectersim/ward"
    visual_rules = calls.visuals[0][1]
    assert visual_rules[0].kwargs["key"] == "bunnyland.spectersim/ward"
    assert visual_rules[0].kwargs["contribution"].kwargs["base_model_key"] == (
        "bunnyland.spectersim/ward"
    )
